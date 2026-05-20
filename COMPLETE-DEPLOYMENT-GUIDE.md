# 🚀 AIRGO DEPLOYMENT GUIDE - COMPLETE WALKTHROUGH

## 📦 WHAT YOU HAVE READY:

✅ Fixed frontend (`index-FIXED-NO-ORPHAN-DIV.html`)
✅ Integrated backend (`backend-CORS-FIXED.py`)  
✅ All API keys (Anthropic, Amadeus, Clerk, Supabase, Resend)
✅ Domain name (bookairgo.online)
✅ Paystack integration
✅ Database schema (Supabase)

---

## 🎯 DEPLOYMENT STEPS (30 MINUTES)

### **STEP 1: Prepare Files for GitHub (5 min)**

1. **Create a new folder** on your computer: `airgo-deployment`

2. **Copy these files into it:**
   - `backend-CORS-FIXED.py` → rename to `backend.py`
   - `index-FIXED-NO-ORPHAN-DIV.html` → rename to `index.html`
   - `my-trips.html` (from project files)
   - `settings-y2k.html` (from project files)
   - `payment-success-y2k.html` (from project files)
   - `requirements.txt` → use `requirements-integrated.txt`
   - `README.md` (I created this)
   - `.gitignore` (standard Python gitignore)

3. **Update `index.html` API endpoint** (line 1162):
   ```javascript
   // BEFORE (temporary URL):
   const API_ENDPOINT = 'https://airgo-backend1.onrender.com/api/chat';
   
   // AFTER (will be your new backend):
   const API_ENDPOINT = 'https://airgo-backend-production.onrender.com/api/chat';
   ```
   **OR wait until you get your backend URL, then update!**

---

### **STEP 2: Push to GitHub (5 min)**

**Open terminal in the `airgo-deployment` folder:**

```bash
# Initialize git
git init

# Add all files
git add .

# Commit
git commit -m "AirGO production deployment - ready for live testing"

# Create main branch
git branch -M main

# Link to GitHub (create repo first on github.com!)
git remote add origin https://github.com/YOUR-USERNAME/airgo.git

# Push
git push -u origin main
```

**GitHub repository is ready!** ✅

---

### **STEP 3: Deploy Backend to Render (10 min)**

1. **Go to Render:** https://dashboard.render.com

2. **Create New Web Service:**
   - Click "New +" → "Web Service"
   - Click "Connect account" → GitHub
   - Select your `airgo` repository
   - Click "Connect"

3. **Configure Service:**
   ```
   Name: airgo-backend-production
   Environment: Python 3
   Region: Oregon (US West) or Frankfurt (closest to Nigeria)
   Branch: main
   Root Directory: (leave blank)
   Build Command: pip install -r requirements.txt
   Start Command: uvicorn backend:app --host 0.0.0.0 --port $PORT
   ```

4. **Select Plan:**
   - Free tier: Good for testing
   - Paid ($7/month): Better for production
   - Click "Create Web Service"

5. **Add Environment Variables:**
   While deploying, click "Environment" tab → Add these 10 variables:

   ```
   ANTHROPIC_API_KEY          → sk-ant-xxxxxxxxxxxxx
   AMADEUS_API_KEY            → xxxxxxxxxxxxx
   AMADEUS_API_SECRET         → xxxxxxxxxxxxx
   CLERK_SECRET_KEY           → sk_test_xxxxxxxxxxxxx
   CLERK_PUBLISHABLE_KEY      → pk_test_xxxxxxxxxxxxx
   SUPABASE_URL               → https://xxxxxxxxxxxxx.supabase.co
   SUPABASE_KEY               → eyJhbGc... (anon key, very long!)
   SUPABASE_SERVICE_KEY       → eyJhbGc... (service_role key, very long!)
   RESEND_API_KEY             → re_xxxxxxxxxxxxx
   RESEND_FROM_EMAIL          → booking@bookairgo.online
   ```

6. **Wait for Deployment** (3-5 minutes)
   - Watch the logs
   - When done, you'll see: ✅ "Live"
   - **Copy your backend URL:** `https://airgo-backend-production-xxxx.onrender.com`

7. **Verify Backend:**
   Open in browser: `https://airgo-backend-production-xxxx.onrender.com/health`
   
   Should see:
   ```json
   {
     "claude_configured": true,
     "amadeus_configured": true,
     "clerk_configured": true,
     "supabase_configured": true,
     "resend_configured": true
   }
   ```

   **If any are `false`:** Check that environment variable!

---

### **STEP 4: Update Frontend API URL (2 min)**

Now that you have your backend URL:

1. **Edit `index.html`** (line 1162)
2. **Update:**
   ```javascript
   const API_ENDPOINT = 'https://airgo-backend-production-xxxx.onrender.com/api/chat';
   ```
   Replace `xxxx` with your actual backend hash!

3. **Commit and push:**
   ```bash
   git add index.html
   git commit -m "Update API endpoint to production backend"
   git push
   ```

---

### **STEP 5: Deploy Frontend to Netlify (8 min)**

1. **Go to Netlify:** https://app.netlify.com

2. **Create New Site:**
   - Click "Add new site" → "Import an existing project"
   - Click "GitHub" → Authorize
   - Select `airgo` repository
   - Click "Deploy site"

3. **Build Settings:**
   ```
   Build command: (leave blank - static site)
   Publish directory: . (just a dot, means root)
   ```
   - Click "Deploy"

4. **Wait for Deployment** (2 minutes)
   - You'll get a URL like: `https://sparkling-unicorn-abc123.netlify.app`

5. **Test Basic Functionality:**
   - Open the Netlify URL
   - Type: "Show me flights from Lagos to Abuja tomorrow"
   - Should see flight cards appear! ✅

---

### **STEP 6: Configure Custom Domain (if ready now)**

**Option A: Point to Netlify Immediately**

1. **In Netlify:**
   - Site settings → Domain management
   - Click "Add custom domain"
   - Enter: `bookairgo.online`
   - Click "Verify"

2. **In Hostinger:**
   - Go to: Domains → bookairgo.online → DNS/Nameservers
   - Option 1: Update nameservers to Netlify's (recommended)
     ```
     dns1.p08.nsone.net
     dns2.p08.nsone.net
     dns3.p08.nsone.net
     dns4.p08.nsone.net
     ```
   - Option 2: Add A record pointing to Netlify's IP
     - Wait 1-24 hours for DNS propagation

3. **SSL Certificate:**
   - Netlify will auto-generate
   - Wait 10-20 minutes
   - Your site will be: `https://bookairgo.online` ✅

**Option B: Keep Netlify URL for Now**
- Just use `https://sparkling-unicorn-abc123.netlify.app` for testing
- Add custom domain later!

---

## ✅ FULL TESTING CHECKLIST

After deployment, test everything:

### **Backend Tests:**
- [ ] `/health` endpoint shows all services true
- [ ] Backend logs show no errors

### **Frontend Tests:**
- [ ] Site loads correctly
- [ ] Chat interface appears
- [ ] Can type messages

### **Integration Tests:**
- [ ] Search "Lagos to Abuja tomorrow" → Flight cards appear
- [ ] Click "BOOK THIS FLIGHT" → Booking form appears
- [ ] Provide passenger details → All fields captured
- [ ] Click payment → Paystack modal opens
- [ ] Use test card (4084 0840 8408 4081) → Payment succeeds
- [ ] Check Supabase → Booking saved in database
- [ ] Check email inbox → Confirmation email received
- [ ] Click "My Trips" → Booking appears in history

### **Mobile Tests:**
- [ ] Open on mobile phone
- [ ] Interface responsive
- [ ] Chat works
- [ ] Booking flow works

**If ALL checked → YOU'RE LIVE!** 🎉

---

## 🔐 ENVIRONMENT VARIABLES REFERENCE

### **Backend (Render) - 10 Variables:**
```
ANTHROPIC_API_KEY          # Claude AI
AMADEUS_API_KEY            # Flight data
AMADEUS_API_SECRET         # Flight data auth
CLERK_SECRET_KEY           # User auth (server)
CLERK_PUBLISHABLE_KEY      # User auth (client)
SUPABASE_URL               # Database URL
SUPABASE_KEY               # Database anon key
SUPABASE_SERVICE_KEY       # Database admin key
RESEND_API_KEY             # Email service
RESEND_FROM_EMAIL          # Sender email address
```

### **Frontend (Netlify) - Optional:**
```
PAYSTACK_PUBLIC_KEY        # Already in HTML, but can be env var
```

---

## 🚨 TROUBLESHOOTING

### **"Health check shows false"**
→ Check environment variable spelling
→ Make sure you copied FULL key (especially Supabase - very long!)
→ Redeploy backend after adding variables

### **"Can't send messages"**
→ Check API_ENDPOINT points to correct backend URL
→ Check browser console for CORS errors
→ Verify backend is running (check /health)

### **"Bookings not saving"**
→ Check Supabase tables exist (run SQL schema if needed)
→ Check SUPABASE_SERVICE_KEY is correct
→ Check backend logs for errors

### **"Emails not arriving"**
→ Verify bookairgo.online domain in Resend
→ Check spam folder
→ Verify DNS records added (SPF, DKIM, MX)
→ Check Resend logs

---

## 🎯 GOING FROM TEST TO PRODUCTION

When ready for real payments:

1. **Paystack:** 
   - Update to `pk_live_` key in HTML
   - Test with real small amount (₦100)

2. **Amadeus:**
   - Already using production keys ✅

3. **Domain:**
   - Already configured (bookairgo.online) ✅

4. **Monitoring:**
   - Check Render logs daily
   - Monitor Supabase database
   - Watch Resend delivery rates
   - Track Paystack transactions

---

## 📞 FINAL CHECKS BEFORE ANNOUNCING

- [ ] Domain points to site (bookairgo.online)
- [ ] SSL certificate active (https://)
- [ ] All integrations working
- [ ] Test bookings completing successfully
- [ ] Emails arriving in inbox (not spam)
- [ ] Mobile experience tested
- [ ] "My Trips" page works
- [ ] Settings page loads
- [ ] Payment success page shows correctly

**When ALL checked → ANNOUNCE YOUR LAUNCH!** 🚀

---

## 🎉 YOU'RE READY TO DEPLOY!

**Time estimate:** 30-45 minutes total
**Difficulty:** Medium (just follow steps carefully!)
**Result:** Live flight booking platform! ✈️

**Start with Step 1 and work through each step!** 💪
