"""
AIRGO Backend Server v3 - Fully Integrated
All 6 services ACTIVE: Claude AI, Amadeus, Supabase, Resend, Clerk, Paystack
"""

from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os, httpx, json, random, re
from datetime import datetime, timedelta
from typing import Optional, List
from supabase import create_client, Client
import resend
from jose import jwt, jwk, JWTError
import anthropic

app = FastAPI(title="AIRGO API", version="3.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"], expose_headers=["*"])

# ============================================
# CONFIGURATION - All 6 Services
# ============================================

# 1. Claude AI
CLAUDE_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
claude_client = None
if CLAUDE_API_KEY:
    try:
        claude_client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
        print("✅ Claude AI connected")
    except Exception as e:
        print(f"❌ Claude init failed: {e}")
else:
    print("⚠️ ANTHROPIC_API_KEY not set")

# 2. Amadeus
AMADEUS_API_KEY = os.getenv("AMADEUS_API_KEY", "")
AMADEUS_API_SECRET = os.getenv("AMADEUS_API_SECRET", "")
AMADEUS_TOKEN_URL = "https://api.amadeus.com/v1/security/oauth2/token"
AMADEUS_FLIGHT_SEARCH_URL = "https://api.amadeus.com/v2/shopping/flight-offers"
print("✅ Amadeus keys loaded" if (AMADEUS_API_KEY and AMADEUS_API_SECRET) else "⚠️ Amadeus keys missing - demo flights only")

# 3. Clerk
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY", "")
CLERK_PUBLISHABLE_KEY = os.getenv("CLERK_PUBLISHABLE_KEY", "")
CLERK_ISSUER = os.getenv("CLERK_ISSUER", "")  # e.g. https://your-app.clerk.accounts.dev
clerk_jwks = None
if CLERK_PUBLISHABLE_KEY and CLERK_ISSUER:
    print(f"✅ Clerk configured (issuer: {CLERK_ISSUER})")
else:
    print("⚠️ Clerk not fully configured - set CLERK_PUBLISHABLE_KEY + CLERK_ISSUER")

# 4. Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase: Client = None
if SUPABASE_URL and SUPABASE_SERVICE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        print("✅ Supabase connected")
    except Exception as e:
        print(f"❌ Supabase init failed: {e}")
        supabase = None
else:
    print("⚠️ Supabase not configured")

# 5. Resend
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "booking@bookairgo.online")
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY
    print("✅ Resend email configured")
else:
    print("⚠️ Resend not set - emails disabled")

# 6. Paystack
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "")
print("✅ Paystack verification ready" if PAYSTACK_SECRET_KEY else "⚠️ Paystack secret not set")


# ============================================
# DATA MODELS
# ============================================

class ChatMessage(BaseModel):
    message: str
    history: Optional[List[dict]] = None

class FlightInfo(BaseModel):
    airline: str
    flight_number: str
    origin: str
    destination: str
    departure_time: str
    arrival_time: str
    price: str
    currency: str
    duration: str
    available_seats: Optional[int] = None

class BookingRequest(BaseModel):
    booking_reference: str
    airline: str
    flight_number: str
    origin: str
    destination: str
    departure_time: str
    arrival_time: Optional[str] = ""
    passenger_name: str
    phone: str
    email: str
    price: float
    currency: str = "NGN"
    payment_method: str = "card"
    payment_reference: str
    flight_date: Optional[str] = ""
    duration: Optional[str] = ""


# ============================================
# CLERK - JWKS JWT Verification
# ============================================

async def fetch_clerk_jwks():
    global clerk_jwks
    if not CLERK_ISSUER:
        return None
    try:
        async with httpx.AsyncClient() as http:
            resp = await http.get(f"{CLERK_ISSUER.rstrip('/')}/.well-known/jwks.json", timeout=10.0)
            if resp.status_code == 200:
                clerk_jwks = resp.json()
                print(f"✅ Clerk JWKS fetched ({len(clerk_jwks.get('keys', []))} keys)")
                return clerk_jwks
    except Exception as e:
        print(f"⚠️ Clerk JWKS fetch failed: {e}")
    return None

async def verify_clerk_token(authorization: str) -> Optional[dict]:
    """Verify Clerk JWT - returns user info or None. NEVER blocks."""
    global clerk_jwks
    if not authorization or not CLERK_ISSUER:
        return None
    token = authorization[7:] if authorization.startswith("Bearer ") else None
    if not token:
        return None
    try:
        if not clerk_jwks:
            await fetch_clerk_jwks()
        if not clerk_jwks:
            return None
        kid = jwt.get_unverified_header(token).get("kid")
        rsa_key = None
        for key in clerk_jwks.get("keys", []):
            if key.get("kid") == kid:
                rsa_key = key
                break
        if not rsa_key:
            await fetch_clerk_jwks()
            for key in (clerk_jwks or {}).get("keys", []):
                if key.get("kid") == kid:
                    rsa_key = key
                    break
        if not rsa_key:
            return None
        payload = jwt.decode(token, rsa_key, algorithms=["RS256"], issuer=CLERK_ISSUER, options={"verify_aud": False})
        return {"clerk_user_id": payload.get("sub"), "email": payload.get("email", ""), "name": payload.get("name", "")}
    except Exception as e:
        print(f"⚠️ Clerk verify: {e}")
        return None


# ============================================
# SUPABASE - Database
# ============================================

async def get_or_create_user(clerk_user_id, email, full_name=None, phone=None):
    if not supabase:
        return None
    try:
        result = supabase.table("users").select("*").eq("clerk_user_id", clerk_user_id).execute()
        if result.data and len(result.data) > 0:
            return result.data[0]
        result = supabase.table("users").insert({"clerk_user_id": clerk_user_id, "email": email, "full_name": full_name, "phone": phone}).execute()
        if result.data:
            print(f"✅ User created: {email}")
            return result.data[0]
        return None
    except Exception as e:
        print(f"❌ User error: {e}")
        return None

async def save_booking(booking: BookingRequest, clerk_user_id: str = None):
    """Save booking to Supabase - ALWAYS runs, auth optional"""
    if not supabase:
        print("⚠️ Supabase unavailable")
        return None
    try:
        data = {
            "booking_reference": booking.booking_reference, "airline": booking.airline,
            "flight_number": booking.flight_number, "origin": booking.origin,
            "destination": booking.destination, "departure_time": booking.departure_time,
            "arrival_time": booking.arrival_time or "", "passenger_name": booking.passenger_name,
            "phone": booking.phone, "email": booking.email, "price": booking.price,
            "currency": booking.currency, "payment_method": booking.payment_method,
            "payment_reference": booking.payment_reference, "flight_date": booking.flight_date or "",
            "duration": booking.duration or "", "payment_status": "completed",
            "status": "confirmed", "booked_at": datetime.now().isoformat(),
        }
        if clerk_user_id:
            data["clerk_user_id"] = clerk_user_id
        result = supabase.table("bookings").insert(data).execute()
        if result.data:
            print(f"✅ Booking saved: {booking.booking_reference}")
            return result.data[0]
        return None
    except Exception as e:
        print(f"❌ Save error: {e}")
        return None

async def get_bookings_by_clerk_id(clerk_user_id):
    if not supabase: return []
    try:
        r = supabase.table("bookings").select("*").eq("clerk_user_id", clerk_user_id).order("booked_at", desc=True).execute()
        return r.data or []
    except: return []

async def get_bookings_by_email(email):
    if not supabase: return []
    try:
        r = supabase.table("bookings").select("*").eq("email", email).order("booked_at", desc=True).execute()
        return r.data or []
    except: return []


# ============================================
# RESEND - Confirmation Email
# ============================================

async def send_booking_confirmation_email(booking: BookingRequest):
    if not RESEND_API_KEY:
        print("⚠️ Resend not configured")
        return False
    try:
        price_display = f"\u20a6{booking.price:,.2f}"
        fdate = booking.flight_date or "See departure time"
        html = f"""<!DOCTYPE html><html><head><style>
body{{font-family:Arial,sans-serif;line-height:1.6;color:#333}}.c{{max-width:600px;margin:0 auto}}
.h{{background:linear-gradient(135deg,#0a0e27,#1a1f3c);color:#00c9a7;padding:30px;text-align:center;border-radius:8px 8px 0 0}}
.h h1{{margin:0;font-size:24px}}.rb{{background:#00c9a7;color:#0a0e27;padding:6px 14px;border-radius:20px;font-weight:bold;display:inline-block;margin-top:10px}}
.ct{{background:#f9f9f9;padding:30px}}.d{{background:white;padding:20px;margin:20px 0;border-left:4px solid #00c9a7;border-radius:4px}}
.r{{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #eee}}.l{{font-weight:bold;color:#666}}.v{{color:#333}}
.p{{font-size:22px;font-weight:bold;color:#00c9a7}}.f{{background:#0a0e27;color:#999;padding:20px;text-align:center;font-size:12px;border-radius:0 0 8px 8px}}
</style></head><body><div class="c">
<div class="h"><h1>AIRGO - Booking Confirmed!</h1><div class="rb">{booking.booking_reference}</div></div>
<div class="ct"><p>Hi {booking.passenger_name},</p><p>Your flight is confirmed!</p>
<div class="d">
<div class="r"><span class="l">Booking Ref</span><span class="v"><b>{booking.booking_reference}</b></span></div>
<div class="r"><span class="l">Flight</span><span class="v">{booking.airline} {booking.flight_number}</span></div>
<div class="r"><span class="l">Route</span><span class="v">{booking.origin} &rarr; {booking.destination}</span></div>
<div class="r"><span class="l">Date</span><span class="v">{fdate}</span></div>
<div class="r"><span class="l">Departure</span><span class="v">{booking.departure_time}</span></div>
<div class="r"><span class="l">Passenger</span><span class="v">{booking.passenger_name}</span></div>
<div class="r"><span class="l">Total Paid</span><span class="p">{price_display}</span></div>
</div>
<h3>Important Reminders:</h3><ul>
<li><b>Check-in opens 24 hours before departure</b></li>
<li><b>Arrive 2 hours early</b> (Lagos traffic!)</li>
<li><b>Bring valid ID</b> - name must match exactly</li>
<li><b>Save this email</b> for check-in</li></ul>
<p>Have a great flight!</p><p>Need help? Visit <b>bookairgo.online</b></p></div>
<div class="f"><p>AIRGO - Nigeria's AI Flight Booking Platform</p><p>Payment Ref: {booking.payment_reference}</p></div>
</div></body></html>"""
        r = resend.Emails.send({"from": RESEND_FROM_EMAIL, "to": [booking.email], "subject": f"Flight Confirmed - {booking.booking_reference} | {booking.origin} to {booking.destination}", "html": html})
        print(f"✅ Email sent to {booking.email}: {r}")
        return True
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False


# ============================================
# AMADEUS - Live + Demo Fallback
# ============================================

class AmadeusClient:
    AIRLINES = [{"name":"Air Peace","prefix":"P4"},{"name":"Arik Air","prefix":"W3"},{"name":"Dana Air","prefix":"9J"},{"name":"ValueJet","prefix":"VK"},{"name":"Green Africa Airways","prefix":"GR"}]
    ROUTES = {
        ("LOS","ABV"):{"d":90,"p":72000},("ABV","LOS"):{"d":90,"p":72000},("LOS","PHC"):{"d":70,"p":58000},("PHC","LOS"):{"d":70,"p":58000},
        ("LOS","KAN"):{"d":120,"p":85000},("KAN","LOS"):{"d":120,"p":85000},("LOS","ENU"):{"d":75,"p":55000},("ENU","LOS"):{"d":75,"p":55000},
        ("ABV","PHC"):{"d":80,"p":65000},("PHC","ABV"):{"d":80,"p":65000},("ABV","KAN"):{"d":60,"p":48000},("KAN","ABV"):{"d":60,"p":48000},
        ("ABV","ENU"):{"d":65,"p":50000},("ENU","ABV"):{"d":65,"p":50000},("LOS","CBQ"):{"d":85,"p":62000},("CBQ","LOS"):{"d":85,"p":62000},
        ("LOS","BNI"):{"d":55,"p":45000},("BNI","LOS"):{"d":55,"p":45000},("LOS","QOW"):{"d":70,"p":52000},("QOW","LOS"):{"d":70,"p":52000},
    }

    def __init__(self):
        self.access_token = None
        self.token_expiry = None
        self.is_live = False

    async def get_token(self):
        if self.access_token and self.token_expiry and datetime.now() < self.token_expiry:
            return self.access_token
        try:
            async with httpx.AsyncClient() as h:
                r = await h.post(AMADEUS_TOKEN_URL, data={"grant_type":"client_credentials","client_id":AMADEUS_API_KEY,"client_secret":AMADEUS_API_SECRET}, timeout=15.0)
                if r.status_code == 200:
                    d = r.json()
                    self.access_token = d["access_token"]
                    self.token_expiry = datetime.now() + timedelta(seconds=d.get("expires_in",1799)-60)
                    return self.access_token
        except: pass
        return None

    async def search_flights(self, origin, destination, date) -> List[FlightInfo]:
        if AMADEUS_API_KEY and AMADEUS_API_SECRET:
            try:
                tok = await self.get_token()
                if tok:
                    async with httpx.AsyncClient() as h:
                        r = await h.get(AMADEUS_FLIGHT_SEARCH_URL, params={"originLocationCode":origin,"destinationLocationCode":destination,"departureDate":date,"adults":1,"max":5,"currencyCode":"NGN"}, headers={"Authorization":f"Bearer {tok}"}, timeout=30.0)
                        if r.status_code == 200:
                            data = r.json()
                            if data.get("data"):
                                parsed = self._parse(data)
                                if parsed:
                                    self.is_live = True
                                    print(f"✅ Live: {origin}->{destination} ({len(parsed)})")
                                    return parsed
            except Exception as e:
                print(f"Live search failed: {e}")
        self.is_live = False
        return self._demo(origin, destination, date)

    def _parse(self, resp) -> List[FlightInfo]:
        flights = []
        for o in (resp.get("data") or [])[:5]:
            try:
                s = o["itineraries"][0]["segments"][0]
                c = s["carrierCode"]
                n = resp.get("dictionaries",{}).get("carriers",{}).get(c,c)
                dep = datetime.fromisoformat(s["departure"]["at"].replace("Z","+00:00"))
                arr = datetime.fromisoformat(s["arrival"]["at"].replace("Z","+00:00"))
                p = o["price"]
                dur = o["itineraries"][0]["duration"].replace("PT","").replace("H","h ").replace("M","m")
                flights.append(FlightInfo(airline=n, flight_number=f"{c}{s['number']}", origin=s["departure"]["iataCode"], destination=s["arrival"]["iataCode"], departure_time=dep.strftime("%I:%M %p"), arrival_time=arr.strftime("%I:%M %p"), price=f"\u20a6{float(p['total']):,.0f}" if p["currency"]=="NGN" else f"{p['total']} {p['currency']}", currency=p["currency"], duration=dur, available_seats=o.get("numberOfBookableSeats")))
            except: continue
        return flights

    def _demo(self, origin, dest, date) -> List[FlightInfo]:
        rt = self.ROUTES.get((origin,dest), {"d":90,"p":70000})
        random.seed(sum(ord(c) for c in date) + hash((origin,dest)))
        als = random.sample(self.AIRLINES, min(random.randint(3,4), len(self.AIRLINES)))
        slots = [(6,8),(9,12),(13,16),(17,20)]
        random.shuffle(slots)
        flights = []
        for i,a in enumerate(als):
            sl = slots[i%4]
            dep = datetime.strptime(f"{random.randint(sl[0],sl[1])}:{random.choice([0,15,30,45]):02d}", "%H:%M")
            arr = dep + timedelta(minutes=rt["d"])
            pr = round(rt["p"] * random.uniform(0.85,1.15)/1000)*1000
            flights.append(FlightInfo(airline=a["name"], flight_number=f"{a['prefix']}{random.randint(100,999)}", origin=origin, destination=dest, departure_time=dep.strftime("%I:%M %p"), arrival_time=arr.strftime("%I:%M %p"), price=f"\u20a6{pr:,.0f}", currency="NGN", duration=f"{rt['d']//60}h {rt['d']%60}m", available_seats=random.randint(3,28)))
        flights.sort(key=lambda f: datetime.strptime(f.departure_time, "%I:%M %p"))
        print(f"📋 Demo: {origin}->{dest} ({len(flights)})")
        return flights

amadeus = AmadeusClient()


# ============================================
# CLAUDE AI
# ============================================

def get_system_prompt():
    today = datetime.now()
    return f"""You are AIRGO, a flight booking assistant for Nigerian travelers.

TODAY'S DATE: {today.strftime('%A, %B %d, %Y')}
Use this to resolve relative dates. If user says "Saturday", calculate the NEXT Saturday. NEVER ask "which Saturday?".

CRITICAL: Show flights in THIS EXACT FORMAT (no emojis, no markdown):

Option 1: Air Peace (P47123)
  LOS -> ABV
  Departs: 08:30 AM | Arrives: 09:45 AM
  Duration: 1h 15m
  Price: \u20a685,000

DO NOT use emojis, markdown bold, or different formatting. The frontend parses this format.

For other messages, be warm and helpful. Keep responses concise.
When users book, collect: Full name, Phone number, Email, Payment method (card/transfer)"""

async def process_with_claude(user_message, flight_data=None, conversation_history=None):
    messages = []
    if conversation_history:
        for msg in conversation_history:
            if msg.get('role') and msg.get('content') and msg['content'] != user_message:
                messages.append({"role": msg['role'], "content": msg['content']})
    ctx = user_message
    if flight_data:
        ctx += "\n\n[FLIGHT DATA - Show to user in EXACT format]\n\n"
        for i, f in enumerate(flight_data[:5], 1):
            ctx += f"Option {i}: {f.airline} ({f.flight_number})\n  {f.origin} -> {f.destination}\n  Departs: {f.departure_time} | Arrives: {f.arrival_time}\n  Duration: {f.duration}\n  Price: {f.price}\n\n"
    messages.append({"role": "user", "content": ctx})
    r = claude_client.messages.create(model="claude-sonnet-4-20250514", max_tokens=800, system=get_system_prompt(), messages=messages)
    return r.content[0].text


# ============================================
# DATE EXTRACTION
# ============================================

def extract_date_from_message(message):
    today = datetime.now()
    msg = message.lower()
    if "today" in msg: return today.strftime("%Y-%m-%d")
    if "tomorrow" in msg: return (today+timedelta(days=1)).strftime("%Y-%m-%d")
    if "next week" in msg: return (today+timedelta(days=7)).strftime("%Y-%m-%d")
    for i,name in enumerate(["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]):
        if name in msg:
            d = i - today.weekday()
            if d <= 0: d += 7
            return (today+timedelta(days=d)).strftime("%Y-%m-%d")
    m = re.search(r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b', message)
    if m: return m.group(0)
    for idx,mn in enumerate(["january","february","march","april","may","june","july","august","september","october","november","december"],1):
        p = re.search(rf'{mn[:3]}\w*\s+(\d{{1,2}})', msg) or re.search(rf'(\d{{1,2}})(?:st|nd|rd|th)?\s+{mn[:3]}', msg)
        if p:
            try:
                t = datetime(today.year, idx, int(p.group(1)))
                if t < today: t = datetime(today.year+1, idx, int(p.group(1)))
                return t.strftime("%Y-%m-%d")
            except: continue
    m = re.search(r'\b(\d{1,2})[/\-](\d{1,2})(?:[/\-](\d{2,4}))?\b', message)
    if m:
        try:
            y = int(m.group(3)) if m.group(3) else today.year
            if y < 100: y += 2000
            return datetime(y, int(m.group(2)), int(m.group(1))).strftime("%Y-%m-%d")
        except: pass
    return (today+timedelta(days=7)).strftime("%Y-%m-%d")


# ============================================
# STARTUP
# ============================================

@app.on_event("startup")
async def startup():
    if CLERK_ISSUER:
        await fetch_clerk_jwks()


# ============================================
# API ENDPOINTS
# ============================================

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", "version": "3.0.0",
        "services": {
            "claude": {"active": claude_client is not None},
            "amadeus": {"active": bool(AMADEUS_API_KEY), "mode": "live" if amadeus.is_live else "demo"},
            "clerk": {"active": bool(CLERK_PUBLISHABLE_KEY and CLERK_ISSUER), "jwks": clerk_jwks is not None},
            "supabase": {"active": supabase is not None},
            "resend": {"active": bool(RESEND_API_KEY)},
            "paystack": {"active": bool(PAYSTACK_SECRET_KEY)},
        }
    }

@app.get("/api/clerk-config")
async def clerk_config():
    """Frontend calls this to get Clerk publishable key"""
    return {"publishable_key": CLERK_PUBLISHABLE_KEY or "", "enabled": bool(CLERK_PUBLISHABLE_KEY)}

@app.post("/api/chat")
async def chat(chat_message: ChatMessage):
    try:
        message = chat_message.message.lower()
        flight_data = None
        codes = {"lagos":"LOS","ikeja":"LOS","abuja":"ABV","port harcourt":"PHC","kano":"KAN","enugu":"ENU","calabar":"CBQ","benin":"BNI","owerri":"QOW"}
        if any(kw in message for kw in ["flight","book","fly"]+list(codes.keys())):
            origin = destination = None
            for city, code in codes.items():
                if city in message:
                    if not origin: origin = code
                    elif code != origin: destination = code
            if origin and destination:
                try:
                    flight_data = await amadeus.search_flights(origin, destination, extract_date_from_message(message))
                except Exception as e:
                    print(f"Flight search error: {e}")
        return {"response": await process_with_claude(chat_message.message, flight_data=flight_data, conversation_history=chat_message.history)}
    except Exception as e:
        import traceback; traceback.print_exc()
        try: return {"response": await process_with_claude(chat_message.message, conversation_history=chat_message.history)}
        except: return {"response": "I'm having a brief connection issue. Please try again in a moment!"}

@app.post("/api/bookings")
async def create_booking(booking: BookingRequest, authorization: str = Header(None)):
    """Create booking: ALWAYS saves to Supabase + sends email. Clerk auth optional but enriches data."""
    try:
        # 1. Clerk auth (optional)
        clerk_user_id = None
        if authorization:
            user_info = await verify_clerk_token(authorization)
            if user_info:
                clerk_user_id = user_info["clerk_user_id"]
                await get_or_create_user(clerk_user_id, booking.email, booking.passenger_name, booking.phone)
                print(f"✅ Authenticated: {clerk_user_id}")

        # 2. Verify Paystack payment
        paystack_verified = False
        if PAYSTACK_SECRET_KEY:
            try:
                async with httpx.AsyncClient() as h:
                    r = await h.get(f"https://api.paystack.co/transaction/verify/{booking.payment_reference}", headers={"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}, timeout=10.0)
                    if r.status_code == 200 and r.json().get("data",{}).get("status") == "success":
                        paystack_verified = True
                        print(f"✅ Paystack verified: {booking.payment_reference}")
                    else:
                        print(f"⚠️ Paystack: {r.json().get('data',{}).get('status','unknown')}")
            except Exception as e:
                print(f"⚠️ Paystack check failed: {e}")

        # 3. Save to Supabase (ALWAYS)
        db_ok = await save_booking(booking, clerk_user_id=clerk_user_id)

        # 4. Send email (ALWAYS)
        email_ok = await send_booking_confirmation_email(booking)

        return {
            "success": True,
            "booking_reference": booking.booking_reference,
            "saved": db_ok is not None,
            "email_sent": email_ok,
            "paystack_verified": paystack_verified,
            "authenticated": clerk_user_id is not None,
            "message": "Booking confirmed! Check your email for details."
        }
    except Exception as e:
        print(f"❌ Booking error: {e}")
        try:
            await save_booking(booking)
            await send_booking_confirmation_email(booking)
        except: pass
        return {"success": True, "booking_reference": booking.booking_reference, "message": "Booking confirmed!"}

@app.get("/api/my-bookings")
async def get_my_bookings(authorization: str = Header(None), email: str = Query(None)):
    """Get bookings by Clerk token (preferred) or email (fallback)"""
    try:
        if authorization:
            user_info = await verify_clerk_token(authorization)
            if user_info and user_info.get("clerk_user_id"):
                bookings = await get_bookings_by_clerk_id(user_info["clerk_user_id"])
                if bookings:
                    return {"bookings": bookings, "source": "clerk"}
        if email:
            return {"bookings": await get_bookings_by_email(email), "source": "email"}
        return {"bookings": [], "message": "Sign in or provide email to see bookings"}
    except Exception as e:
        print(f"Bookings error: {e}")
        return {"bookings": []}
