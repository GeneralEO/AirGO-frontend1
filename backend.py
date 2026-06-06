# DATABASE OPERATIONS (SUPABASE)
"""
AIRGO Backend Server - Clean Version
No Clerk SDK - just Supabase, Resend, and Anthropic
"""

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import httpx
from datetime import datetime, timedelta
from typing import Optional, List
import json

from supabase import create_client, Client
import resend
from jose import jwt, JWTError
import anthropic


app = FastAPI(title="AIRGO API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://bookairgo.online",
        "https://www.bookairgo.online",
        "https://airgo-frontend-enym.onrender.com",
        "http://localhost:3000",  # Local dev only
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# CONFIGURATION
# ============================================
 
# Claude AI
CLAUDE_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
client = None
if CLAUDE_API_KEY:
    try:
        client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
    except Exception as e:
        print("Claude init failed:", e)
 
# Amadeus
AMADEUS_API_KEY = os.getenv("AMADEUS_API_KEY", "")
AMADEUS_API_SECRET = os.getenv("AMADEUS_API_SECRET", "")
AMADEUS_TOKEN_URL = "https://api.amadeus.com/v1/security/oauth2/token"  # PRODUCTION
AMADEUS_FLIGHT_SEARCH_URL = "https://api.amadeus.com/v2/shopping/flight-offers"  # PRODUCTION
 
# Clerk
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY", "")
CLERK_PUBLISHABLE_KEY = os.getenv("CLERK_PUBLISHABLE_KEY", "")

# Flutterwave
FLUTTERWAVE_SECRET_KEY = os.getenv("FLW_SECRET_KEY", "")
 
# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase: Client = None

if SUPABASE_URL and SUPABASE_SERVICE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        print("✅ Supabase connected")
    except Exception as e:
        print("❌ Supabase init failed:", e)
        supabase = None
else:
    print("⚠️ Missing Supabase env variables")
 
# Resend
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "booking@bookairgo.online")
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY
 
# Check configuration
if not CLAUDE_API_KEY:
    print("WARNING: ANTHROPIC_API_KEY not set")
if not AMADEUS_API_KEY:
    print("WARNING: AMADEUS_API_KEY not set - using test mode")
if not CLERK_SECRET_KEY:
    print("WARNING: CLERK_SECRET_KEY not set - auth disabled")
if not FLUTTERWAVE_SECRET_KEY:
    print("WARNING: FLW_SECRET_KEY not set - payments cannot be verified")
if not SUPABASE_URL:
    print("WARNING: SUPABASE_URL not set - database disabled")
if not RESEND_API_KEY:
    print("WARNING: RESEND_API_KEY not set - emails disabled")
 
 
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
    user_id: str
    booking_reference: str
    airline: str
    flight_number: str
    origin: str
    destination: str
    departure_time: str
    arrival_time: Optional[str] = None
    passenger_name: str
    phone: str
    email: str
    price: float
    currency: str = "NGN"
    payment_method: str
    payment_reference: str                    # tx_ref YOU generated — used as the Flutterwave ref check
    transaction_id: Optional[str] = None      # Flutterwave's own transaction id from the callback
    flw_transaction_id: Optional[str] = None  # alias kept for backwards compat
    flight_offer: Optional[dict] = None       # raw Amadeus offer, for re-pricing (optional)
 
 
# ============================================
# AUTHENTICATION (CLERK)
# ============================================
 
_jwks_cache: dict = {}

async def _get_clerk_jwks() -> dict:
    """Fetch and cache Clerk's public JWKS."""
    import base64
    pk = CLERK_PUBLISHABLE_KEY or ""
    # pk_live_<base64_domain> — strip prefix and decode
    b64 = pk.replace("pk_live_", "").replace("pk_test_", "")
    # Add padding
    b64 += "=" * (-len(b64) % 4)
    try:
        frontend_api = base64.b64decode(b64).decode("utf-8").rstrip("$")
    except Exception:
        raise HTTPException(status_code=500, detail="Invalid CLERK_PUBLISHABLE_KEY")

    jwks_url = f"https://{frontend_api}/.well-known/jwks.json"
    async with httpx.AsyncClient() as h:
        resp = await h.get(jwks_url, timeout=10.0)
        if resp.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to fetch Clerk JWKS")
        return resp.json()


async def verify_clerk_token(authorization: str = Header(None)) -> dict:
    """Verify Clerk JWT using the public key from Clerk's JWKS endpoint."""
    if not authorization:
        raise HTTPException(status_code=401, detail="No authorization header")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")

    token = authorization.split(" ")[1]

    try:
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        jwks = await _get_clerk_jwks()

        rsa_key = {}
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                rsa_key = {k: key[k] for k in ("kty", "kid", "use", "n", "e") if k in key}
                break

        if not rsa_key:
            raise HTTPException(status_code=401, detail="No matching public key found in JWKS")

        from jose import jwk as jose_jwk
        public_key = jose_jwk.construct(rsa_key)

        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            options={"verify_aud": False}
        )
        return {
            "user_id": payload.get("sub"),
            "email": payload.get("email"),
            "name": payload.get("name")
        }
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
 
 
# ============================================
# DATABASE OPERATIONS (SUPABASE)
# ============================================
 
async def get_or_create_user(clerk_user_id: str, email: str, full_name: str = None, phone: str = None):
    """Get user from database or create if doesn't exist"""
    if not supabase:
        return None
    
    # Check if user exists
    result = supabase.table("users").select("*").eq("clerk_user_id", clerk_user_id).execute()
    
    if result.data and len(result.data) > 0:
        return result.data[0]
    
    # Create new user
    new_user = {
        "clerk_user_id": clerk_user_id,
        "email": email,
        "full_name": full_name,
        "phone": phone
    }
    
    result = supabase.table("users").insert(new_user).execute()
    return result.data[0] if result.data else None


async def resolve_user(clerk_user_id, email: str, full_name: str = None, phone: str = None):
    """
    Find or create a user. Works with OR without a Clerk id.
    Order: clerk_user_id → email → create new row.
    NOTE: users.clerk_user_id must be NULLABLE in Supabase for guest bookings.
    """
    if not supabase:
        return None
    try:
        if clerk_user_id:
            res = supabase.table("users").select("*").eq("clerk_user_id", clerk_user_id).execute()
            if res.data:
                return res.data[0]
        # Fall back to email lookup (covers guest + signed-in users whose row exists)
        if email:
            res = supabase.table("users").select("*").eq("email", email).execute()
            if res.data:
                return res.data[0]
        # Create a new row
        new_user = {
            "clerk_user_id": clerk_user_id,   # may be None — that's fine
            "email": email,
            "full_name": full_name,
            "phone": phone,
        }
        res = supabase.table("users").insert(new_user).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"resolve_user error: {e}")
        return None


async def save_booking_to_database(booking: BookingRequest, user_db_id: str):
    """Save booking to Supabase database"""
    if not supabase:
        print("Supabase not configured - booking not saved to database")
        return None
    
    try:
        booking_data = {
            "user_id": user_db_id,
            "booking_reference": booking.booking_reference,
            "airline": booking.airline,
            "flight_number": booking.flight_number,
            "origin": booking.origin,
            "destination": booking.destination,
            "departure_time": booking.departure_time,
            "arrival_time": booking.arrival_time,
            "passenger_name": booking.passenger_name,
            "phone": booking.phone,
            "email": booking.email,
            "price": booking.price,
            "currency": booking.currency,
            "payment_method": booking.payment_method,
            "payment_reference": booking.payment_reference,
            "payment_status": "completed",
            "status": "confirmed"
        }
        
        result = supabase.table("bookings").insert(booking_data).execute()
        return result.data[0] if result.data else None
    
    except Exception as e:
        print(f"Error saving booking to database: {e}")
        return None
 
 
async def verify_flutterwave_payment(
    transaction_id: str,
    expected_amount: float,
    expected_reference: str,
    expected_currency: str = "NGN",
) -> dict:
    """
    Returns {"verified": bool, "reason": str, "data": dict|None}.
    Checks all four facts: status, amount, currency, tx_ref.
    Never raises — failures are returned as {"verified": False, ...}.
    """
    if not FLUTTERWAVE_SECRET_KEY:
        return {"verified": False, "reason": "payment_not_configured", "data": None}
    if not transaction_id:
        return {"verified": False, "reason": "missing_transaction_id", "data": None}

    url = f"https://api.flutterwave.com/v3/transactions/{transaction_id}/verify"
    headers = {"Authorization": f"Bearer {FLUTTERWAVE_SECRET_KEY}"}

    try:
        async with httpx.AsyncClient() as http:
            resp = await http.get(url, headers=headers, timeout=30.0)
    except Exception as e:
        print(f"Flutterwave verify network error: {e}")
        return {"verified": False, "reason": "verify_unreachable", "data": None}

    if resp.status_code != 200:
        print(f"Flutterwave verify failed: {resp.status_code} - {resp.text}")
        return {"verified": False, "reason": "verify_failed", "data": None}

    data = resp.json().get("data", {})

    status_ok   = data.get("status") == "successful"
    amount_ok   = float(data.get("amount", 0)) >= float(expected_amount)
    currency_ok = data.get("currency") == expected_currency
    ref_ok      = (not expected_reference) or (data.get("tx_ref") == expected_reference)

    if status_ok and amount_ok and currency_ok and ref_ok:
        return {"verified": True, "reason": "ok", "data": data}

    print(f"Flutterwave mismatch -> status={status_ok} amount={amount_ok} "
          f"currency={currency_ok} ref={ref_ok}")
    return {"verified": False, "reason": "verification_mismatch", "data": data}


async def get_user_bookings(user_db_id: str):
    """Get all bookings for a user"""
    if not supabase:
        return []
    
    try:
        result = supabase.table("bookings")\
            .select("*")\
            .eq("user_id", user_db_id)\
            .order("created_at", desc=True)\
            .execute()
        
        return result.data if result.data else []
    
    except Exception as e:
        print(f"Error fetching bookings: {e}")
        return []
 
 
# ============================================
# EMAIL (RESEND)
# ============================================
 
async def send_booking_confirmation_email(booking: BookingRequest):
    """Send booking confirmation email via Resend"""
    if not RESEND_API_KEY:
        print("Resend not configured - email not sent")
        return False
    
    try:
        email_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #0a0e27, #1a1f3c); color: #00c9a7; padding: 30px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 28px; }}
                .content {{ background: #f9f9f9; padding: 30px; }}
                .flight-details {{ background: white; padding: 20px; margin: 20px 0; border-left: 4px solid #00c9a7; }}
                .detail-row {{ display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #eee; }}
                .detail-label {{ font-weight: bold; color: #666; }}
                .detail-value {{ color: #333; }}
                .footer {{ background: #0a0e27; color: #999; padding: 20px; text-align: center; font-size: 12px; }}
                .price {{ font-size: 24px; font-weight: bold; color: #00c9a7; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✈️ AIRGO - Booking Confirmed!</h1>
                </div>
                
                <div class="content">
                    <p>Hi {booking.passenger_name},</p>
                    
                    <p>Great news! Your flight booking is confirmed. Here are your details:</p>
                    
                    <div class="flight-details">
                        <div class="detail-row">
                            <span class="detail-label">Booking Reference</span>
                            <span class="detail-value"><strong>{booking.booking_reference}</strong></span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Flight</span>
                            <span class="detail-value">{booking.airline} {booking.flight_number}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Route</span>
                            <span class="detail-value">{booking.origin} → {booking.destination}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Departure</span>
                            <span class="detail-value">{booking.departure_time}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Passenger</span>
                            <span class="detail-value">{booking.passenger_name}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Total Paid</span>
                            <span class="price">₦{booking.price:,.2f}</span>
                        </div>
                    </div>
                    
                    <h3>⚠️ Important Reminders:</h3>
                    <ul>
                        <li><strong>Check-in opens 24 hours before departure</strong></li>
                        <li><strong>Arrive 2 hours early</strong> (Lagos traffic!)</li>
                        <li><strong>Bring valid ID</strong> - name must match exactly</li>
                        <li><strong>Save this email</strong> for check-in</li>
                    </ul>
                    
                    <p>Have a great flight! 🎉</p>
                    
                    <p>Need help? Reply to this email or visit <strong>bookairgo.online</strong></p>
                </div>
                
                <div class="footer">
                    <p>AIRGO - Nigeria's AI Flight Booking Platform</p>
                    <p>Payment Reference: {booking.payment_reference}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        params = {
            "from": RESEND_FROM_EMAIL,
            "to": [booking.email],
            "subject": f"✈️ Flight Confirmed - {booking.booking_reference}",
            "html": email_html
        }
        
        email = resend.Emails.send(params)
        print(f"Confirmation email sent: {email}")
        return True
        
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
 
 
# ============================================
# AMADEUS API CLIENT
# ============================================
 
class AmadeusClient:
    """Handles Amadeus API authentication and requests"""
    
    def __init__(self):
        self.api_key = AMADEUS_API_KEY
        self.api_secret = AMADEUS_API_SECRET
        self.access_token = None
        self.token_expiry = None
    
    async def get_access_token(self):
        """Get or refresh Amadeus access token"""
        if self.access_token and self.token_expiry and datetime.now() < self.token_expiry:
            return self.access_token
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                AMADEUS_TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.api_key,
                    "client_secret": self.api_secret
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data["access_token"]
                expires_in = data.get("expires_in", 1799)
                self.token_expiry = datetime.now() + timedelta(seconds=expires_in - 60)
                return self.access_token
            else:
                raise HTTPException(status_code=500, detail="Failed to get Amadeus access token")
    
    async def search_flights(self, origin: str, destination: str, departure_date: str, adults: int = 1):
        """Search for flights using Amadeus API"""
        token = await self.get_access_token()
        
        params = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": departure_date,
            "adults": adults,
            "max": 5,
            "currencyCode": "NGN"
        }
        
        headers = {"Authorization": f"Bearer {token}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                AMADEUS_FLIGHT_SEARCH_URL,
                params=params,
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Amadeus API error: {response.status_code} - {response.text}")
                return None
    
    def parse_flight_data(self, amadeus_response: dict) -> List[FlightInfo]:
        """Parse Amadeus API response into FlightInfo objects"""
        if not amadeus_response or "data" not in amadeus_response:
            return []
        
        flights = []
        
        for offer in amadeus_response["data"][:5]:
            try:
                itinerary = offer["itineraries"][0]
                segment = itinerary["segments"][0]
                
                airline_code = segment["carrierCode"]
                flight_number = f"{airline_code}{segment['number']}"
                airline_name = amadeus_response.get("dictionaries", {}).get("carriers", {}).get(airline_code, airline_code)
                
                departure = segment["departure"]
                arrival = segment["arrival"]
                
                dep_time = datetime.fromisoformat(departure["at"].replace("Z", "+00:00"))
                arr_time = datetime.fromisoformat(arrival["at"].replace("Z", "+00:00"))
                
                price_info = offer["price"]
                price = price_info["total"]
                currency = price_info["currency"]
                
                duration = itinerary["duration"].replace("PT", "").replace("H", "h ").replace("M", "m")
                
                flight = FlightInfo(
                    airline=airline_name,
                    flight_number=flight_number,
                    origin=departure['iataCode'],
                    destination=arrival['iataCode'],
                    departure_time=dep_time.strftime("%I:%M %p"),
                    arrival_time=arr_time.strftime("%I:%M %p"),
                    price=f"₦{float(price):,.0f}" if currency == "NGN" else f"{price} {currency}",
                    currency=currency,
                    duration=duration,
                    available_seats=offer.get("numberOfBookableSeats")
                )
                
                flights.append(flight)
                
            except Exception as e:
                print(f"Error parsing flight: {e}")
                continue
        
        return flights

    async def confirm_price(self, flight_offer: dict):
        """
        Re-validate a flight offer right before charging via Amadeus Flight Offers Price.
        Returns {"price": float, "currency": str, "raw": dict} or None on any failure.
        """
        token = await self.get_access_token()
        url = "https://api.amadeus.com/v1/shopping/flight-offers/pricing"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {"data": {"type": "flight-offers-pricing", "flightOffers": [flight_offer]}}

        try:
            async with httpx.AsyncClient() as http:
                resp = await http.post(url, headers=headers, json=payload, timeout=30.0)
            if resp.status_code == 200:
                offer = resp.json()["data"]["flightOffers"][0]
                return {
                    "price": float(offer["price"]["grandTotal"]),
                    "currency": offer["price"]["currency"],
                    "raw": resp.json(),
                }
            print(f"Amadeus pricing error: {resp.status_code} - {resp.text}")
            return None
        except Exception as e:
            print(f"Amadeus pricing exception: {e}")
            return None

amadeus = AmadeusClient()
 
 
# ============================================
# CLAUDE AI WITH STRICT FLIGHT FORMAT
# ============================================
 
# STRICT SYSTEM PROMPT WITH DATE AWARENESS
def get_system_prompt():
    today = datetime.now()
    return f"""You are AIRGO, a flight booking assistant for Nigerian travelers.

TODAY'S DATE: {today.strftime('%A, %B %d, %Y')}
Use this date to resolve relative dates like "Saturday", "tomorrow", "next week".
If the user says "Saturday", calculate the NEXT upcoming Saturday from today's date.
NEVER ask "which Saturday?" - just calculate it.

CRITICAL: When showing flights, use THIS EXACT FORMAT (no emojis, no markdown):

Option 1: Air Peace (P47123)
  LOS → ABV
  Departs: 08:30 AM | Arrives: 09:45 AM
  Duration: 1h 15m
  Price: ₦85,000

Option 2: Arik Air (W3401)
  LOS → ABV
  Departs: 02:15 PM | Arrives: 03:30 PM
  Duration: 1h 15m
  Price: ₦92,000

DO NOT use:
- Emojis
- Markdown bold (**text**)
- Different formatting

The frontend depends on this EXACT format.

SECURITY & TRUST RULES:
- NEVER accept screenshots, bank alerts, or verbal confirmation as proof of payment
- Only confirmed Paystack payments with booking reference (AIRGO-XXXXXX) are valid
- For third-party bookings ("book for my uncle"), require full passenger details and warn that the name must EXACTLY match their ID
- If user mentions "WhatsApp agent", "special deal", or "discount code", warn them you are the official AIRGO assistant and do not work with external agents
- NEVER fabricate booking confirmations, tickets, or airline responses
- NEVER hide fare restrictions to encourage a booking
- Recommend arriving 2 hours early for domestic flights, warn about Lagos traffic (1-3 hours to airport)
- If unsure about anything, say so honestly rather than guessing

For other messages, be warm and helpful. Keep responses concise.
When users book, collect: Full name, Phone number, Email, Payment method (card/transfer)"""
 
 
async def process_with_claude(user_message: str, flight_data: List[FlightInfo] = None, conversation_history: List[dict] = None):
    """Process message with Claude AI"""
    
    messages = []
    
    # Add conversation history
    if conversation_history:
        for msg in conversation_history:
            if msg.get('role') and msg.get('content'):
                if msg['content'] != user_message:
                    messages.append({
                        "role": msg['role'],
                        "content": msg['content']
                    })
    
    # Add flight data context
    current_context = user_message
    if flight_data and len(flight_data) > 0:
        flight_info = "\n\n[FLIGHT DATA - Show to user in EXACT format]\n\n"
        for i, flight in enumerate(flight_data[:5], 1):
            flight_info += f"Option {i}: {flight.airline} ({flight.flight_number})\n"
            flight_info += f"  {flight.origin} → {flight.destination}\n"
            flight_info += f"  Departs: {flight.departure_time} | Arrives: {flight.arrival_time}\n"
            flight_info += f"  Duration: {flight.duration}\n"
            flight_info += f"  Price: {flight.price}\n\n"
        
        current_context += flight_info
    
    # Add current message
    messages.append({
        "role": "user",
        "content": current_context
    })
    
    # Call Claude
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=800,
        system=get_system_prompt(),
        messages=messages
    )
    
    return response.content[0].text
 
 
# ============================================
# API ENDPOINTS
# ============================================
 
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "claude_configured": bool(CLAUDE_API_KEY),
        "amadeus_configured": bool(AMADEUS_API_KEY),
        "clerk_configured": bool(CLERK_SECRET_KEY),
        "supabase_configured": bool(SUPABASE_URL),
        "resend_configured": bool(RESEND_API_KEY)
    }
 
 
# ============================================
# DATE EXTRACTION FROM USER MESSAGE
# ============================================

def extract_date_from_message(message: str) -> str:
    """Parse natural language dates from user message. Returns YYYY-MM-DD string."""
    import re
    
    today = datetime.now()
    msg = message.lower()
    
    # "today"
    if "today" in msg:
        return today.strftime("%Y-%m-%d")
    
    # "tomorrow" + common misspellings
    tomorrow_variants = ["tomorrow", "tommorow", "tommorrow", "tmrw", "2moro", "2morrow", "tomoro"]
    if any(t in msg for t in tomorrow_variants):
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Compound: "next week Friday", "next week Monday", etc.
    day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    import re
    next_week_day = re.search(r'next\s+week\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)', msg)
    if next_week_day:
        target_day = next_week_day.group(1)
        target_idx = day_names.index(target_day)
        current_weekday = today.weekday()
        days_ahead = (7 - current_weekday) + target_idx  # Next week's occurrence
        return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    
    # "next week" (standalone — must come AFTER compound check)
    if "next week" in msg:
        return (today + timedelta(days=7)).strftime("%Y-%m-%d")
    
    # Day names: "monday", "tuesday", "saturday", etc.
    day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for i, day_name in enumerate(day_names):
        if day_name in msg:
            # Calculate next occurrence of this day
            current_weekday = today.weekday()  # 0=Monday
            days_ahead = i - current_weekday
            if days_ahead <= 0:  # Target day already passed this week
                days_ahead += 7
            target_date = today + timedelta(days=days_ahead)
            return target_date.strftime("%Y-%m-%d")
    
    # ISO date: "2026-03-28"
    iso_match = re.search(r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b', message)
    if iso_match:
        return iso_match.group(0)
    
    # Month name + day: "March 29", "29th March", "Mar 29"
    month_names = ["january", "february", "march", "april", "may", "june",
                   "july", "august", "september", "october", "november", "december"]
    for month_idx, month_name in enumerate(month_names, 1):
        short = month_name[:3]
        # "March 29" or "Mar 29"
        pattern1 = re.search(rf'{short}\w*\s+(\d{{1,2}})', msg)
        # "29th March" or "29 Mar"  
        pattern2 = re.search(rf'(\d{{1,2}})(?:st|nd|rd|th)?\s+{short}', msg)
        
        match = pattern1 or pattern2
        if match:
            day = int(match.group(1))
            year = today.year
            try:
                target = datetime(year, month_idx, day)
                # If the date has passed, assume next year
                if target < today:
                    target = datetime(year + 1, month_idx, day)
                return target.strftime("%Y-%m-%d")
            except ValueError:
                continue
    
    # DD/MM or DD/MM/YYYY
    date_match = re.search(r'\b(\d{1,2})[/\-](\d{1,2})(?:[/\-](\d{2,4}))?\b', message)
    if date_match:
        day = int(date_match.group(1))
        month = int(date_match.group(2))
        year_str = date_match.group(3)
        year = int(year_str) if year_str else today.year
        if year < 100:
            year += 2000
        try:
            return datetime(year, month, day).strftime("%Y-%m-%d")
        except ValueError:
            pass
    
    # Default: 7 days from now
    return (today + timedelta(days=7)).strftime("%Y-%m-%d")


@app.post("/api/chat")
async def chat(chat_message: ChatMessage):
    try:
        message = chat_message.message.lower()
        
        flight_data = None

        if any(keyword in message for keyword in ["flight", "book", "fly", "lagos", "abuja", "port harcourt", "kano", "enugu", "calabar", "benin", "owerri"]):
            origin = None
            destination = None
            
            # City to IATA mapping
            city_codes = {
                "lagos": "LOS", "ikeja": "LOS",
                "abuja": "ABV",
                "port harcourt": "PHC",
                "kano": "KAN",
                "enugu": "ENU",
                "calabar": "CBQ",
                "benin": "BNI",
                "owerri": "QOW",
            }
            
            # Smart direction detection using context clues
            import re
            found_cities = []
            for city, code in city_codes.items():
                if city in message:
                    found_cities.append((city, code, message.index(city)))
            
            if len(found_cities) >= 2:
                # Sort by position in message
                found_cities.sort(key=lambda x: x[2])
                
                # Check for directional keywords
                for city, code, pos in found_cities:
                    # "to Lagos", "going to Abuja", "travel to Kano"
                    to_pattern = re.search(rf'(?:to|into|towards|heading\s+to|going\s+to|travel\s+to|fly\s+to|flying\s+to)\s+{city}', message)
                    # "from Lagos", "leaving Lagos", "im in Lagos", "i am in Lagos"
                    from_pattern = re.search(rf'(?:from|leaving|depart|im\s+in|i\s+am\s+in|i\'m\s+in|based\s+in|live\s+in)\s+{city}', message)
                    
                    if to_pattern:
                        destination = code
                    elif from_pattern:
                        origin = code
                
                # Fallback: if only one direction detected, assign the other
                if origin and not destination:
                    destination = [c[1] for c in found_cities if c[1] != origin][0]
                elif destination and not origin:
                    origin = [c[1] for c in found_cities if c[1] != destination][0]
                elif not origin and not destination:
                    # No directional clues — use message order (first=origin, second=destination)
                    origin = found_cities[0][1]
                    destination = found_cities[1][1]
            
            elif len(found_cities) == 1:
                # Only one city mentioned — can't search without both
                origin = found_cities[0][1]

            # Smart date extraction from user message
            departure_date = extract_date_from_message(message)
            
            if origin and destination:
                try:
                    amadeus_response = await amadeus.search_flights(origin, destination, departure_date)
                    if amadeus_response:
                        flight_data = amadeus.parse_flight_data(amadeus_response)
                        if not flight_data:
                            print(f"WARNING: parse_flight_data returned empty for {origin}->{destination}")
                except Exception as flight_err:
                    print(f"Flight search error: {flight_err}")
                    flight_data = None
        
        ai_response = await process_with_claude(
            chat_message.message,
            flight_data=flight_data,
            conversation_history=chat_message.history
        )
        
        return {"response": ai_response}
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"response": "Hmm, something went sideways on my end. Could you try that again? If it keeps happening, try rephrasing your request."}
 
 
@app.post("/api/bookings")
async def create_booking(booking: BookingRequest, authorization: str = Header(None)):
    """
    Confirmation pipeline — 4 ordered steps:
    1. Verify payment with Flutterwave  (hard gate)
    2. Re-price with Amadeus            (only if flight_offer provided)
    3. Save to Supabase                 (works with or without Clerk)
    4. Send Resend confirmation email   (only after verified payment)
    """
    # --- Soft auth: use Clerk if present, never block saving on it ---
    clerk_user_id = None
    if authorization:
        try:
            info = await verify_clerk_token(authorization)
            clerk_user_id = info.get("user_id")
        except Exception:
            clerk_user_id = None  # guest booking — that's fine

    # --- STEP 1: VERIFY PAYMENT (hard gate — nothing saves without this) ---
    txn_id = booking.transaction_id or booking.flw_transaction_id or booking.payment_reference
    payment = await verify_flutterwave_payment(
        transaction_id=txn_id,
        expected_amount=booking.price,
        expected_reference=booking.payment_reference,
        expected_currency=booking.currency or "NGN",
    )
    if not payment["verified"]:
        print(f"Payment verification failed: {payment['reason']}")
        return {
            "success": False,
            "message": (
                "We couldn't confirm your payment just yet. If money left your "
                "account, nothing is lost — please give it a moment and try again. "
                "Still stuck? Reach us at booking@bookairgo.online and we'll sort it."
            ),
        }

    verified_amount = float(payment["data"].get("amount", booking.price))

    # --- STEP 2: RE-PRICE (optional — only runs if the raw offer was sent) ---
    if booking.flight_offer:
        priced = await amadeus.confirm_price(booking.flight_offer)
        if priced and priced["price"] > verified_amount:
            print(f"Price drift: paid {verified_amount}, current {priced['price']}")
            return {
                "success": False,
                "message": (
                    "That fare updated while you were checking out, so we've paused "
                    "before confirming a seat. Please reopen the flight to see the "
                    "latest price — your payment will be handled fairly either way."
                ),
            }

    # --- STEP 3: SAVE TO SUPABASE (works with or without Clerk) ---
    saved = None
    user = await resolve_user(clerk_user_id, booking.email, booking.passenger_name, booking.phone)
    if user:
        saved = await save_booking_to_database(booking, user["id"])
    else:
        print("User could not be resolved/created — booking not saved to DB")

    # --- STEP 4: CONFIRMATION EMAIL (only after verified payment) ---
    await send_booking_confirmation_email(booking)

    return {
        "success": True,
        "booking_reference": booking.booking_reference,
        "saved": bool(saved),
        "message": "Booking confirmed! Check your email for details.",
    }
 
 
@app.get("/api/my-bookings")
async def get_my_bookings(authorization: str = Header(None)):
    """Get user's booking history (requires authentication)"""
    try:
        # Verify user
        user_info = await verify_clerk_token(authorization)
        
        # Get user from database
        if supabase:
            result = supabase.table("users").select("*").eq("clerk_user_id", user_info["user_id"]).execute()
            if result.data and len(result.data) > 0:
                user_db_id = result.data[0]["id"]
                bookings = await get_user_bookings(user_db_id)
                return {"bookings": bookings}
        
        return {"bookings": []}
        
    except Exception as e:
        print(f"Get bookings error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
 

