# ⚡ AIRGO DEPLOYMENT - QUICK COMMANDS

## 📦 FILES YOU NEED:

1. **backend.py** → Use `backend-CORS-FIXED.py` (rename it)
2. **index.html** → Use `index-FIXED-NO-ORPHAN-DIV.html` (rename it)
3. **requirements.txt** → Use requirements-integrated.txt (rename it)
4. **my-trips.html** → From project files
5. **settings-y2k.html** → From project files  
6. **payment-success-y2k.html** → From project files
7. **README.md** → I created this
8. **.gitignore** → Standard Python gitignore

---

## 🚀 DEPLOYMENT COMMANDS

### **1. Initialize Git:**
```bash
git init
git add .
git commit -m "AirGO production deployment"
git branch -M main
```

### **2. Create GitHub Repo:**
- Go to: https://github.com/new
- Name: `airgo`
- Make it Private
- Don't initialize with README
- Click "Create repository"

### **3. Push to GitHub:**
```bash
git remote add origin https://github.com/YOUR-USERNAME/airgo.git
git push -u origin main
```

---

## 🔧 RENDER BACKEND SETUP

### **Create Web Service:**
```
Name: airgo-backend-production
Environment: Python 3
Build: pip install -r requirements.txt
Start: uvicorn backend:app --host 0.0.0.0 --port $PORT
```

### **Environment Variables (10 total):**
```
ANTHROPIC_API_KEY=sk-ant-xxxxx
AMADEUS_API_KEY=xxxxx
AMADEUS_API_SECRET=xxxxx
CLERK_SECRET_KEY=sk_test_xxxxx
CLERK_PUBLISHABLE_KEY=pk_test_xxxxx
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGc... (anon key)
SUPABASE_SERVICE_KEY=eyJhbGc... (service key)
RESEND_API_KEY=re_xxxxx
RESEND_FROM_EMAIL=booking@bookairgo.online
```

---

## 🌐 NETLIFY FRONTEND SETUP

### **Deploy:**
1. Import from GitHub
2. Build command: (leave blank)
3. Publish directory: `.`
4. Deploy!

### **Add Custom Domain:**
1. Domain management → Add domain
2. Enter: `bookairgo.online`
3. Update Hostinger DNS with Netlify nameservers

---

## ✅ VERIFICATION:

### **Backend:**
```
https://your-backend.onrender.com/health
→ All services should be "true"
```

### **Frontend:**
```
Type: "Lagos to Abuja tomorrow"
→ Flight cards should appear
```

### **Full Flow:**
1. Search flights ✅
2. Book flight ✅
3. Pay (test card: 4084 0840 8408 4081) ✅
4. Check Supabase → Booking saved ✅
5. Check email → Confirmation received ✅

---

## 🔄 UPDATE COMMANDS

### **After getting backend URL:**
```bash
# Update index.html with new API endpoint
git add index.html
git commit -m "Update API endpoint"
git push
```

### **Future updates:**
```bash
git add .
git commit -m "Description of changes"
git push
# Render and Netlify auto-deploy!
```

---

## 🚨 QUICK FIXES

### **Backend not working:**
```bash
# Check logs in Render dashboard
# Verify all 10 environment variables
# Redeploy if needed
```

### **Frontend can't connect:**
```bash
# Check API_ENDPOINT in index.html (line 1162)
# Should be: https://your-backend.onrender.com/api/chat
# Update and push
```

---

## 📞 EMERGENCY CONTACTS

**Backend URL:** Get from Render dashboard after deployment
**Frontend URL:** Get from Netlify after deployment
**Custom Domain:** bookairgo.online (configure in Netlify)

---

**DEPLOYMENT TIME: 30-45 MINUTES** ⏱️  
**READY TO GO LIVE!** 🚀
