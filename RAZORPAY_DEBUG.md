# 🔧 Razorpay Button Not Working - Debugging Guide

## Quick Fix Checklist

### 1️⃣ Make Sure .env File Exists

**Check if .env file exists in your project root:**

```bash
# List files in project root
dir

# You should see: .env
```

**If .env doesn't exist, create it:**

Create a file named `.env` (no extension) in `c:\Users\balak\Bookex Chelf\`

Add this content:
```
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxxx
RAZORPAY_KEY_SECRET=your_secret_key
```

Replace with your actual keys from Razorpay dashboard.

---

### 2️⃣ Restart Flask After Editing .env

**Very Important:** Flask needs to be restarted to load .env

```bash
# Stop Flask (Ctrl+C in terminal)
# Then restart:
python app.py
```

---

### 3️⃣ Debug the Button Click

**Follow these steps:**

1. Open browser: `http://localhost:5000/pricing`
2. Press **F12** to open Developer Tools
3. Go to **Console** tab
4. Click the "🇮🇳 Pay with UPI/Card (Razorpay)" button
5. Look at the console for messages

**What you should see:**
- If successful: "handler" message will appear
- If error: Red error message showing what's wrong

---

### 4️⃣ Check Flask Logs

**Look at your Flask terminal when you click the button:**

You should see:
```
POST /create-razorpay-order
```

If you see an error like:
```
ERROR: RAZORPAY_KEY_ID not found in environment!
```

This means your .env file is not being loaded.

---

### 5️⃣ Verify .env File Format

**Common mistakes:**

❌ Wrong: `RAZORPAY_KEY_ID = rzp_test_xxxxx` (spaces around =)
✅ Right: `RAZORPAY_KEY_ID=rzp_test_xxxxx` (no spaces)

❌ Wrong: Key value has quotes
✅ Right: `RAZORPAY_KEY_ID=rzp_test_xxxxx` (no quotes)

❌ Wrong: File saved as .env.txt
✅ Right: File saved as .env (no extension)

---

## Step-by-Step Setup

### Step 1: Create .env File

Open Notepad (or VS Code) and create a new file with:

```
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxxx
RAZORPAY_KEY_SECRET=your_secret_here
```

Save it as `.env` in: `c:\Users\balak\Bookex Chelf\`

### Step 2: Get Your Keys

1. Go to: https://razorpay.com
2. Login to your dashboard
3. Go to: **Settings** → **API Keys** → **TEST MODE**
4. Copy: **Key ID** (starts with rzp_test_)
5. Copy: **Key Secret**

### Step 3: Paste Keys in .env

```
RAZORPAY_KEY_ID=rzp_test_1234567890abcd
RAZORPAY_KEY_SECRET=abcd1234567890efgh
```

Save the file.

### Step 4: Restart Flask

In your terminal:
```bash
# Stop Flask: Press Ctrl+C
# Then run:
python app.py
```

### Step 5: Test Again

1. Go to: http://localhost:5000/pricing
2. Click: "🇮🇳 Pay with UPI/Card (Razorpay)"
3. Razorpay popup should open!

---

## Troubleshooting

### Problem: "Razorpay key not found" Alert

**Cause:** .env file not created or keys not added

**Solution:**
1. Create .env file with keys (see above)
2. Restart Flask
3. Try again

### Problem: Nothing Happens When Clicking Button

**Causes:**
1. .env file not loaded
2. Flask not restarted
3. JavaScript error

**Solution:**
1. Open browser console (F12)
2. Click button again
3. Look for error messages
4. Fix the error shown

### Problem: Order Creation Failed

**Cause:** Invalid Razorpay keys

**Solution:**
1. Copy keys directly from Razorpay dashboard
2. Make sure no extra spaces
3. Check it's TEST MODE, not LIVE MODE
4. Paste exactly as shown

### Problem: "Order creation failed: invalid_key_id"

**Cause:** Wrong API key format

**Solution:**
- Key ID should start with `rzp_test_`
- Key Secret should be a long string
- Both should be from Razorpay dashboard Settings → API Keys

---

## Testing Razorpay Payment

Once button works:

1. Click "🇮🇳 Pay with UPI/Card (Razorpay)"
2. Razorpay popup opens
3. Select "UPI" method
4. Enter test UPI: `success@razorpay`
5. Click "Complete"
6. Payment should succeed!

---

## Verify Everything Works

After payment:
1. You should see: "Payment successful! Premium activated."
2. Redirected to: `/dashboard`
3. Check database: User should have `is_premium = True`

---

## File Locations

```
Project Root: c:\Users\balak\Bookex Chelf\

Files you need:
├── .env                          (Create this - has your keys)
├── app.py                        (Already updated)
├── templates/pricing.html        (Already updated)
└── models/book.py               (User model ready)
```

---

## Checklist

- [ ] .env file created in project root
- [ ] RAZORPAY_KEY_ID added to .env
- [ ] RAZORPAY_KEY_SECRET added to .env
- [ ] Flask restarted (Ctrl+C, then python app.py)
- [ ] Go to /pricing page
- [ ] Click Razorpay button
- [ ] Popup opens
- [ ] Select test UPI: success@razorpay
- [ ] Complete payment
- [ ] Dashboard shows premium ✓

---

## Quick Command to Verify Keys are Loaded

Run this command:
```bash
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('RAZORPAY_KEY_ID:', os.getenv('RAZORPAY_KEY_ID'))
print('RAZORPAY_KEY_SECRET:', os.getenv('RAZORPAY_KEY_SECRET')[:10] + '...' if os.getenv('RAZORPAY_KEY_SECRET') else 'NOT SET')
"
```

You should see your actual keys, not "None" or "NOT SET".

---

## Still Not Working?

1. Open browser console (F12) and click button again
2. Copy any error message
3. Share the error message for more help

Check the console carefully - it will tell you exactly what's wrong!
