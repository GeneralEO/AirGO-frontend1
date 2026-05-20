# ✅ AIRGO DEPLOYMENT MASTER CHECKLIST

## 📦 PRE-DEPLOYMENT CHECKLIST

### **Files Ready:**
- [ ] backend-CORS-FIXED.py (rename to `backend.py`)
- [ ] index-FIXED-NO-ORPHAN-DIV.html (rename to `index.html`)
- [ ] requirements-integrated.txt (rename to `requirements.txt`)
- [ ] my-trips.html
- [ ] settings-y2k.html
- [ ] payment-success-y2k.html
- [ ] README.md
- [ ] .gitignore

### **API Keys Ready:**
- [ ] ANTHROPIC_API_KEY (starts with `sk-ant-`)
- [ ] AMADEUS_API_KEY
- [ ] AMADEUS_API_SECRET
- [ ] CLERK_SECRET_KEY (starts with `sk_test_` or `sk_live_`)
- [ ] CLERK_PUBLISHABLE_KEY (starts with `pk_test_` or `pk_live_`)
- [ ] SUPABASE_URL (https://xxxxx.supabase.co)
- [ ] SUPABASE_KEY (anon key - very long!)
- [ ] SUPABASE_SERVICE_KEY (service_role key - very long!)
- [ ] RESEND_API_KEY (starts with `re_`)
- [ ] Paystack public key (in HTML - `pk_test_` or `pk_live_`)

### **Accounts Created:**
- [ ] GitHub account
- [ ] Render account
- [ ] Netlify account
- [ ] Domain registrar access (Hostinger)

---

## 🚀 DEPLOYMENT STEPS

### **PHASE 1: GitHub (10 minutes)**
- [ ] Created folder: `airgo-deployment`
- [ ] Copied all 8 files into folder
- [ ] Renamed files correctly
- [ ] Initialized git: `git init`
- [ ] Added files: `git add .`
- [ ] Committed: `git commit -m "Initial deployment"`
- [ ] Created GitHub repo
- [ ] Linked repo: `git remote add origin ...`
- [ ] Pushed: `git push -u origin main`
- [ ] ✅ Code is on GitHub!

### **PHASE 2: Backend Deployment (15 minutes)**
- [ ] Logged into Render
- [ ] Created new Web Service
- [ ] Connected GitHub repo
- [ ] Configured:
  - [ ] Name: `airgo-backend-production`
  - [ ] Environment: Python 3
  - [ ] Build: `pip install -r requirements.txt`
  - [ ] Start: `uvicorn backend:app --host 0.0.0.0 --port $PORT`
- [ ] Added environment variables (all 10)
- [ ] Clicked "Create Web Service"
- [ ] Waited for deployment (3-5 min)
- [ ] **Copied backend URL:** `https://________________.onrender.com`
- [ ] Tested `/health` endpoint
- [ ] All services show `true`
- [ ] ✅ Backend is live!

### **PHASE 3: Frontend Update (5 minutes)**
- [ ] Updated `index.html` line 1162 with backend URL
- [ ] Committed change: `git commit -m "Update API endpoint"`
- [ ] Pushed: `git push`
- [ ] ✅ Frontend updated!

### **PHASE 4: Frontend Deployment (10 minutes)**
- [ ] Logged into Netlify
- [ ] Created new site from GitHub
- [ ] Selected `airgo` repo
- [ ] Deployed (build command: blank, publish: `.`)
- [ ] Waited for deployment (2-3 min)
- [ ] **Copied frontend URL:** `https://________________.netlify.app`
- [ ] Tested site - typed message
- [ ] Flight search works
- [ ] ✅ Frontend is live!

### **PHASE 5: Domain Configuration (Optional - 30 min)**
- [ ] Netlify: Added custom domain `bookairgo.online`
- [ ] Hostinger: Updated DNS nameservers OR A record
- [ ] Waited for DNS propagation (10 min - 24 hours)
- [ ] SSL certificate generated
- [ ] Tested: `https://bookairgo.online`
- [ ] ✅ Custom domain works!

---

## 🧪 TESTING CHECKLIST

### **Backend Tests:**
- [ ] `/health` shows all 5 services: `true`
- [ ] No errors in Render logs
- [ ] Backend responds to requests

### **Frontend Tests:**
- [ ] Site loads
- [ ] Chat interface appears
- [ ] Can type messages
- [ ] Send button works
- [ ] Enter key works

### **Integration Tests:**
- [ ] Searched: "Lagos to Abuja tomorrow"
- [ ] Flight cards appeared
- [ ] Clicked "BOOK THIS FLIGHT"
- [ ] Filled passenger details
- [ ] Paystack modal opened
- [ ] Used test card: 4084 0840 8408 4081
- [ ] Payment succeeded
- [ ] Redirected to success page
- [ ] Checked Supabase - booking saved
- [ ] Checked email - confirmation received
- [ ] Opened "My Trips" - booking appears

### **Mobile Tests:**
- [ ] Tested on mobile phone
- [ ] Interface responsive
- [ ] Chat works
- [ ] Booking flow works

### **Domain Tests (if configured):**
- [ ] `bookairgo.online` loads
- [ ] SSL certificate active (https)
- [ ] All features work on custom domain

---

## 🎯 PRODUCTION READY CHECKLIST

### **Before Announcing:**
- [ ] All test bookings work perfectly
- [ ] Email confirmations arriving
- [ ] Database saving bookings
- [ ] No console errors
- [ ] Mobile experience tested
- [ ] All pages load correctly
- [ ] Payment flow smooth
- [ ] Terms & Privacy pages (if needed)

### **When Going Live (Real Payments):**
- [ ] Switch Paystack to `pk_live_` key
- [ ] Test with small real payment (₦100)
- [ ] Verify real booking flow
- [ ] Monitor first few transactions
- [ ] Check Paystack dashboard
- [ ] Announce launch! 🎉

---

## 📊 POST-DEPLOYMENT MONITORING

### **Daily Checks:**
- [ ] Render backend logs - any errors?
- [ ] Supabase database - bookings saving?
- [ ] Resend dashboard - emails delivering?
- [ ] Paystack dashboard - payments processing?

### **Weekly Checks:**
- [ ] User feedback
- [ ] Error patterns
- [ ] Performance issues
- [ ] Database growth

---

## 🚨 EMERGENCY CONTACTS

**If something breaks:**
1. Check Render logs first
2. Check browser console
3. Check backend /health endpoint
4. Verify environment variables
5. Redeploy if needed

**Support:**
- obioraezeezeugo@yahoo.com
- edidiongwillie777@gmail.com

---

## 🎉 SUCCESS CRITERIA

**YOU'RE LIVE WHEN:**
- [ ] Backend deployed and healthy
- [ ] Frontend deployed and accessible
- [ ] Complete booking flow works
- [ ] Emails arrive
- [ ] Database saves bookings
- [ ] Domain points to site (optional)
- [ ] SSL active
- [ ] Mobile works
- [ ] No critical errors

**WHEN ALL CHECKED → YOU'RE LIVE!** 🚀✈️

---

## 📝 DEPLOYMENT TIMELINE

**Estimated Times:**
- GitHub setup: 10 minutes
- Backend deployment: 15 minutes
- Frontend deployment: 10 minutes
- Testing: 15 minutes
- Domain setup (optional): 30 minutes

**Total: 30-60 minutes** (depending on DNS propagation)

---

## 🔄 MAINTENANCE

### **Regular Updates:**
```bash
# Make changes
git add .
git commit -m "Description"
git push

# Render and Netlify auto-deploy!
```

### **Emergency Rollback:**
```bash
git revert HEAD
git push
# Services will redeploy to previous version
```

---

**START AT PHASE 1 AND CHECK OFF EACH ITEM!** ✅

**YOU'VE GOT THIS!** 💪
