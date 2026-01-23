# 🇮🇳 Book Chelf - India Payment Setup (Razorpay Only)

## Why Only Razorpay?

**Stripe doesn't support receiving payments in India.** Razorpay is the best solution for Indian businesses and works perfectly for your use case.

---

## ⚡ Quick Setup (10 minutes)

### Step 1: Create Razorpay Account

**You don't need a website to start!**

1. Go to: https://razorpay.com
2. Click "Sign up"
3. Enter email and set password
4. Verify email
5. Fill in business details:
   - Business name: Book Chelf
   - Business type: Software/App
   - Location: Your city/state
6. Wait for approval (usually 1-2 hours)

### Step 2: Get Test API Keys

Once approved, go to **Settings → API Keys**

You'll see two sections:

```
TEST MODE (Use this for development):
├─ Key ID: rzp_test_xxxxx ← Copy this
└─ Key Secret: xxxxx ← Copy this

LIVE MODE (Use this for real payments):
├─ Key ID: rzp_live_xxxxx
└─ Key Secret: xxxxx
```

**For now, copy the TEST MODE keys**

### Step 3: Create .env File

In your project root, create `.env` file:

```
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxxx
RAZORPAY_KEY_SECRET=your_secret_key_here
```

### Step 4: Test Payment

1. Start Flask: `python app.py`
2. Go to: http://localhost:5000/pricing
3. Click "🇮🇳 Pay with UPI/Card (Razorpay)"
4. Razorpay popup appears
5. Use test UPI: `success@razorpay`
6. Click "Complete payment"
7. Check dashboard - you should be PREMIUM! ✓

---

## 🎯 How to Test Without a Website

Razorpay **test mode works perfectly on localhost** (http://localhost:5000). You don't need a live website to test!

### Test Credentials:

**For Success:**
- UPI ID: `success@razorpay`
- Or use test cards:
  - Visa: `4111111111111111`
  - Mastercard: `5555555555554444`
  - Expiry: Any future date
  - CVV: Any 3 digits

**For Failure (to test error handling):**
- UPI ID: `failed@razorpay`

---

## 📋 Step-by-Step Account Setup

### Razorpay Sign Up

```
1. Visit: https://razorpay.com
2. Click: "Sign up"
3. Enter: 
   - Email: your@email.com
   - Password: Strong password
4. Click: "Sign up"
5. Verify: Check email, click link
6. Fill in:
   - Business Name: Book Chelf
   - Business Type: Technology / Software
   - Your Name
   - Phone: Your number
   - Location: Your city
7. Click: "Continue"
8. Wait: 1-2 hours for approval email
9. Approve: Accept terms via email
```

### Get API Keys

```
After approval:
1. Login: https://dashboard.razorpay.com
2. Go to: Settings (bottom left)
3. Click: "API Keys"
4. You see two tabs:
   - TEST MODE (blue)
   - LIVE MODE (red)
5. TEST MODE is selected
6. Copy: Key ID (starts with rzp_test_)
7. Copy: Key Secret
```

### Create .env File

```bash
# In your project root directory
# Create a file named: .env

# Paste this:
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxxxxxx
RAZORPAY_KEY_SECRET=yyyyyyyyyyyyyyyy
```

---

## 🧪 Testing the Payment System

### Test Scenario 1: Successful Payment

```
1. Open: http://localhost:5000/pricing
2. Login (if not logged in)
3. Click: "🇮🇳 Pay with UPI/Card (Razorpay)"
4. Razorpay popup opens
5. Select: "UPI" 
6. Enter: success@razorpay
7. Click: "Proceed to Payment"
8. See: "Payment successful!"
9. Click: "OK"
10. Redirected: To /dashboard
11. Check: Your profile shows PREMIUM badge ⭐
```

### Test Scenario 2: Failed Payment

```
1. Open: http://localhost:5000/pricing
2. Click: "🇮🇳 Pay with UPI/Card (Razorpay)"
3. Razorpay popup opens
4. Select: "UPI"
5. Enter: failed@razorpay
6. Click: "Proceed to Payment"
7. See: "Payment failed"
8. Check: You're still NOT premium (as expected)
```

### Test Scenario 3: Using Test Card

```
1. Open: http://localhost:5000/pricing
2. Click: "🇮🇳 Pay with UPI/Card (Razorpay)"
3. Razorpay popup opens
4. Select: "Credit/Debit Card"
5. Enter:
   - Card: 4111111111111111
   - Expiry: 12/25
   - CVV: 123
6. Click: "Complete Payment"
7. See: "Payment successful!"
```

---

## 📊 Payment Settings

### Current Price
```
Amount: ₹299
Duration: 365 days (one-time payment)
Currency: INR
```

### To Change Price

Edit [app.py](app.py) and find:

```python
@app.route('/create-razorpay-order', methods=['POST'])
def create_razorpay_order():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    data = {
        'amount': 29900,  # ← Change this (in paise)
        # 29900 paise = ₹299
        # 49900 paise = ₹499
        # 99900 paise = ₹999
```

---

## 🚀 Deployment: From Localhost to Live Website

When you get a website (example.com), you'll need to:

### Step 1: Update Razorpay Settings

1. Go to: Settings → Website URL
2. Enter: https://example.com
3. Click: "Save"

### Step 2: Switch to Live API Keys

1. Go to: Settings → API Keys
2. Click: "LIVE MODE" tab
3. Copy: New Key ID (rzp_live_...)
4. Copy: New Key Secret

### Step 3: Update .env File

```
RAZORPAY_KEY_ID=rzp_live_xxxxxxxxxxxx
RAZORPAY_KEY_SECRET=yyyyyyyyyyyyyy
```

### Step 4: Restart Application

That's it! You're now accepting real payments.

---

## 🔒 Security

✅ HMAC-SHA256 signature verification
✅ Payment signature validated before activating premium
✅ Session authentication (must be logged in)
✅ Amount hardcoded (can't be changed by user)

---

## 💡 Features You Can Access in Test Mode

With just Razorpay test keys, you can:
- ✅ Test complete payment flow
- ✅ Test success scenarios
- ✅ Test failure scenarios
- ✅ Verify database updates
- ✅ Verify premium features unlock
- ✅ Test signature verification
- ✅ No real charges

---

## 🆘 Troubleshooting

### Problem: "API Key not found"
**Solution:** Check that .env file exists in project root with correct keys

### Problem: Razorpay popup doesn't open
**Solution:** 
1. Check browser console (F12)
2. Verify RAZORPAY_KEY_ID is set in .env
3. Restart Flask after editing .env

### Problem: Payment shows error after clicking "Complete"
**Solution:**
1. Check Flask logs (terminal)
2. Verify Key Secret is correct
3. Try again with test credentials

### Problem: Payment succeeds but user not premium
**Solution:**
1. Check database for user record
2. Check if is_premium field updated
3. Restart browser and refresh dashboard

---

## 📞 Support

### Razorpay Support
- Website: https://razorpay.com/support
- Email: support@razorpay.com
- Phone: Available in dashboard

### Common Razorpay Issues
1. **Approval delayed?** Check spam folder for approval email
2. **Test mode not working?** Verify Key ID format (rzp_test_...)
3. **Payment stuck?** Try in incognito/private window

---

## ✅ Checklist

- [ ] Razorpay account created
- [ ] Email verified
- [ ] KYC approved
- [ ] API keys copied
- [ ] .env file created with keys
- [ ] Flask app restarted
- [ ] Test payment successful
- [ ] Premium status shows on dashboard
- [ ] Premium features accessible
- [ ] Ready to deploy when you have website!

---

## 🎯 What's Next?

### Now (Development):
1. Test payments thoroughly
2. Verify all features work
3. Ensure errors are handled

### Later (When you have a website):
1. Update Razorpay with website URL
2. Switch to live API keys
3. Update .env file
4. Deploy to live server
5. Start accepting real payments!

---

## 💰 Razorpay Pricing

### Good News:
- No upfront costs
- No monthly fees
- You only pay per transaction
- Fees: ~1.79% + ₹0 to ₹3 per transaction (check current)
- Instant settlements to your bank account

---

**You're all set to start accepting payments in India!** 🎉

Start with the "Quick Setup" section above and you'll be testing payments in 10 minutes.
