# ✈️ AIRGO - AI-Powered Flight Booking Platform

**Live at:** https://bookairgo.online

AirGO is Nigeria's first AI-driven flight booking platform, making domestic aviation accessible to everyone through conversational AI.

---

## 🚀 QUICK DEPLOY TO GITHUB

### **Step 1: Create GitHub Repository**
```bash
git init
git add .
git commit -m "Initial AirGO deployment - ready for live testing"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/airgo.git
git push -u origin main
```

---

## 📋 BACKEND DEPLOYMENT (Render)

### **1. Create Web Service on Render:**
- Go to: https://dashboard.render.com
- Click "New +" → "Web Service"
- Connect your GitHub repository
- Configure:
  - **Name:** `airgo-backend-production`
  - **Environment:** Python 3
  - **Build Command:** `pip install -r requirements.txt`
  - **Start Command:** `uvicorn backend:app --host 0.0.0.0 --port $PORT`

### **2. Add Environment Variables:**

Go to Environment tab and add these **10 variables**:

```
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx
AMADEUS_API_KEY=xxxxxxxxxxxxx
AMADEUS_API_SECRET=xxxxxxxxxxxxx
CLERK_SECRET_KEY=sk_test_xxxxxxxxxxxxx (or sk_live_ for production)
CLERK_PUBLISHABLE_KEY=pk_test_xxxxxxxxxxxxx (or pk_live_)
SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SUPABASE_KEY=eyJhbGc... (anon key)
SUPABASE_SERVICE_KEY=eyJhbGc... (service_role key - very long!)
RESEND_API_KEY=re_xxxxxxxxxxxxx
RESEND_FROM_EMAIL=booking@bookairgo.online
```

### **3. Deploy and Get Backend URL:**
- Click "Create Web Service"
- Wait for deployment (3-5 minutes)
- Copy URL: `https://airgo-backend-production-xxxx.onrender.com`

---

## 🌐 FRONTEND DEPLOYMENT (Netlify)

### **1. Update API Endpoint:**
Before deploying, update `index.html` line 1162:

```javascript
const API_ENDPOINT = 'https://YOUR-BACKEND-URL.onrender.com/api/chat';
```

Replace with your actual Render backend URL!

### **2. Deploy to Netlify:**
- Go to: https://app.netlify.com
- Click "Add new site" → "Import an existing project"
- Connect GitHub repo
- Build settings: (leave defaults for static site)
- Click "Deploy"

### **3. Configure Custom Domain:**
- Site settings → Domain management
- Add: `bookairgo.online`
- Update Hostinger DNS with Netlify nameservers
- Wait for SSL certificate (auto)

---

## ✅ VERIFICATION CHECKLIST

### **Backend Health Check:**
Visit: `https://your-backend-url.onrender.com/health`

Should return:
```json
{
  "claude_configured": true,
  "amadeus_configured": true,
  "clerk_configured": true,
  "supabase_configured": true,
  "resend_configured": true
}
```

**If any are `false`:** Check that environment variable in Render!

### **Frontend Test:**
1. Open your site
2. Type: "Show flights from Lagos to Abuja tomorrow"
3. Should see flight cards appear
4. Click "BOOK THIS FLIGHT"
5. Fill details, complete payment (use test card)
6. Check Supabase - booking should be saved
7. Check email - confirmation should arrive

---

## 🧪 TEST MODE vs PRODUCTION MODE

### **Test Mode (Current):**
```
Paystack: pk_test_ac3e463ada188c03c07a6812ba30b5eb6e9b0d36
Amadeus: Test API keys
Test Card: 4084 0840 8408 4081
```

### **Production Mode (When Ready):**
```
Paystack: pk_live_xxxxxxxxxxxxx
Amadeus: Production API keys
Real Card: Customer's actual card
```

**To go live:** Just update the environment variables!

---

## 📁 PROJECT FILES

```
airgo/
├── backend.py                 # Backend server (FastAPI)
├── requirements.txt           # Python dependencies
├── index.html                 # Main chat page (FIXED - no orphan div)
├── my-trips.html             # Booking history
├── settings-y2k.html         # User settings
├── payment-success-y2k.html  # Payment success page
├── README.md                 # This file
├── .gitignore               # Ignore secrets
└── render.yaml              # Render config (optional)
```

---

## 🔒 SECURITY - NEVER COMMIT:

```
❌ .env files
❌ API keys
❌ Database passwords
❌ Secret tokens
❌ Private keys
```

**All secrets go in environment variables on Render/Netlify!**

---

## 🌍 DOMAIN SETUP

### **1. Point Domain to Netlify:**
- Hostinger → Domains → bookairgo.online → DNS
- Update nameservers to Netlify's

### **2. Verify Domain in Resend:**
- Resend → Domains → Add bookairgo.online
- Add DNS records (TXT, MX, SPF, DKIM)
- Wait for verification

### **3. Update Backend CORS:**
In `backend.py`, update line 26:
```python
allow_origins=[
    "https://bookairgo.online",
    "https://www.bookairgo.online",
    "http://localhost:8000",
],
```

---

## 📊 MONITORING

**Backend Logs:** Render dashboard → Your service → Logs
**Email Delivery:** Resend dashboard → Logs
**Database:** Supabase dashboard → Table editor
**Analytics:** Netlify dashboard → Analytics

---

## 🚀 GO LIVE STEPS

1. ✅ Deploy backend to Render
2. ✅ Deploy frontend to Netlify
3. ✅ Point bookairgo.online to Netlify
4. ✅ Verify domain in Resend
5. ✅ Test complete booking flow
6. ✅ Switch Paystack to live mode (when ready)
7. ✅ Announce launch! 🎉

---

## 📞 SUPPORT

**Team:**
- obioraezeezeugo@yahoo.com
- edidiongwillie777@gmail.com

**Website:** bookairgo.online

---

## 📄 LICENSE

Proprietary - AirGO © 2026

---

**Ready to deploy! Push to GitHub and follow deployment steps!** ✈️
