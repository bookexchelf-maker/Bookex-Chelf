# Payment System - Step-by-Step Setup Guide

## Quick Start (5 minutes)

### Step 1: Install Payment Libraries
```bash
pip install stripe razorpay requests
```
✓ Already done! Check your requirements.txt

### Step 2: Get API Keys from Payment Providers

#### Get Stripe Keys (for international card payments)

1. Visit https://dashboard.stripe.com
2. Sign up with your email
3. Go to: Dashboard → Developers → API Keys
4. Copy these:
   - **Secret Key** (starts with `sk_test_`)
   - **Publishable Key** (starts with `pk_test_`)

5. Set up Webhook:
   - Go to: Developers → Webhooks
   - Click "Add endpoint"
   - Endpoint URL: `http://localhost:5000/webhook/stripe` (for local testing)
   - Select event: `checkout.session.completed`
   - Copy the **Signing Secret** (starts with `whsec_`)

#### Get Razorpay Keys (for UPI/Card payments in India)

1. Visit https://razorpay.com
2. Sign up with business details
3. Verify email and phone
4. Go to: Settings → API Keys
5. Copy these:
   - **Key ID** (starts with `rzp_test_`)
   - **Key Secret**

6. Enable payment methods in Settings:
   - UPI ✓
   - Cards ✓
   - Netbanking ✓

### Step 3: Create .env File

Create a `.env` file in your project root:

```bash
# Flask
SECRET_KEY=your-secret-key-here
FLASK_ENV=development

# Stripe (replace with your actual keys)
STRIPE_SECRET_KEY=sk_test_xxxxxxxxxxxxx
STRIPE_PUBLIC_KEY=pk_test_xxxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxx

# Razorpay (replace with your actual keys)
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxxx
RAZORPAY_KEY_SECRET=xxxxxxxxxxxxx
```

### Step 4: Test the Payment System

#### Option A: Using Stripe (Test Card)

1. Navigate to `http://localhost:5000/pricing`
2. Click "Pay with Card (Stripe)"
3. Use test card: `4242 4242 4242 4242`
4. Enter any future expiry date
5. Enter any 3-digit CVC
6. Click "Complete payment"
7. You should be redirected to dashboard with premium activated ✓

#### Option B: Using Razorpay (Test UPI)

1. Navigate to `http://localhost:5000/pricing`
2. Click "Pay with UPI/Card (Razorpay)"
3. Razorpay popup opens
4. Select "UPI" method
5. Enter test UPI: `success@razorpay`
6. Click "Complete payment"
7. You should see success message and redirect to dashboard ✓

---

## Detailed Setup Instructions

### Setting up Stripe (International Payments)

#### 1. Create Stripe Account

```
URL: https://dashboard.stripe.com
1. Click "Sign up"
2. Enter email, password
3. Verify email
4. Fill in business details
5. Set your country
```

#### 2. Get API Keys

```
Dashboard → Developers → API Keys

You'll see two sections:

TEST MODE:
┌────────────────────────────────────┐
│ Secret key: sk_test_xxxxx          │ ← Copy this
│ Publishable key: pk_test_xxxxx     │ ← Copy this
└────────────────────────────────────┘

LIVE MODE:
┌────────────────────────────────────┐
│ (Don't use these yet - for         │
│  production only)                  │
└────────────────────────────────────┘
```

#### 3. Set Up Webhooks

```
Developers → Webhooks

Click "Add endpoint"

Endpoint details:
- URL: http://localhost:5000/webhook/stripe
  (For production: https://yourdomain.com/webhook/stripe)
- Version: Latest (default)
- Events: checkout.session.completed

After creating, copy the Signing secret (whsec_xxxxx)
```

#### 4. Add to .env

```
STRIPE_SECRET_KEY=sk_test_xxxxxxxxxxxxx
STRIPE_PUBLIC_KEY=pk_test_xxxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxx
```

#### 5. Test Payment

In test mode, use these test cards:

| Card | Number | Expiry | CVC |
|------|--------|--------|-----|
| Visa | 4242 4242 4242 4242 | Any future | Any 3 digits |
| Visa Debit | 4000 0027 6000 3335 | Any future | Any 3 digits |
| Mastercard | 5555 5555 5555 4444 | Any future | Any 3 digits |

**To simulate failure:**
- Card: 4000 0000 0000 0002
- Expiry: Any future date
- CVC: Any 3 digits

---

### Setting up Razorpay (Indian Payments)

#### 1. Create Razorpay Account

```
URL: https://razorpay.com
1. Click "Sign up"
2. Enter email
3. Set password
4. Verify email
5. Enter business details
6. Verify phone number
```

#### 2. Get API Keys

```
Settings → API Keys

TEST MODE:
┌────────────────────────────────────┐
│ Key ID: rzp_test_xxxxx             │ ← Copy this
│ Key Secret: xxxxx                  │ ← Copy this
└────────────────────────────────────┘

LIVE MODE:
┌────────────────────────────────────┐
│ (Don't use these yet - for         │
│  production only)                  │
└────────────────────────────────────┘
```

#### 3. Enable Payment Methods

```
Settings → Payment Methods

Enable:
☑ UPI
☑ Cards
☑ Netbanking
☑ Wallets (Optional)
```

#### 4. Add to .env

```
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxxx
RAZORPAY_KEY_SECRET=xxxxxxxxxxxxx
```

#### 5. Test Payment

In test mode, use these test UPI IDs:

| UPI ID | Result |
|--------|--------|
| success@razorpay | ✓ Payment succeeds |
| failed@razorpay | ✗ Payment fails |

You can also test with test cards (if enabled):
- Visa: 4111111111111111
- Mastercard: 5555555555554444

---

## Complete Setup Checklist

### Pre-Setup
- [ ] Python 3.8+ installed
- [ ] Flask application running locally
- [ ] Git initialized (optional but recommended)

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```
- [ ] stripe installed
- [ ] razorpay installed
- [ ] requests installed

### Step 2: Stripe Setup
- [ ] Stripe account created
- [ ] API keys copied
- [ ] Webhook configured and tested
- [ ] Keys added to .env

### Step 3: Razorpay Setup
- [ ] Razorpay account created
- [ ] API keys copied
- [ ] Payment methods enabled
- [ ] Keys added to .env

### Step 4: Environment Configuration
- [ ] .env file created in project root
- [ ] STRIPE_SECRET_KEY added
- [ ] STRIPE_WEBHOOK_SECRET added
- [ ] RAZORPAY_KEY_ID added
- [ ] RAZORPAY_KEY_SECRET added
- [ ] DATABASE_URL configured (if needed)

### Step 5: Database Setup
- [ ] Database tables created
- [ ] User model has premium fields:
  - [ ] is_premium (Boolean)
  - [ ] premium_since (DateTime)
  - [ ] premium_until (DateTime)

### Step 6: Application Setup
- [ ] app.py has payment imports
- [ ] Payment routes added:
  - [ ] /create-checkout-session
  - [ ] /payment/success
  - [ ] /webhook/stripe
  - [ ] /create-razorpay-order
  - [ ] /verify-razorpay-payment
- [ ] pricing.html template exists
- [ ] Payment buttons display correctly

### Step 7: Testing
- [ ] Stripe test payment works
- [ ] Razorpay test payment works
- [ ] User becomes premium after payment
- [ ] Dashboard shows premium status
- [ ] Premium features accessible

### Step 8: Security
- [ ] .env file in .gitignore
- [ ] Webhook signatures verified
- [ ] Payment amounts hardcoded (no user input)
- [ ] HTTPS enabled (for production)

---

## Testing Payments Locally

### Using Stripe CLI for Webhooks (Optional but Recommended)

Stripe webhooks won't work on localhost without forwarding. Use Stripe CLI:

1. Install Stripe CLI: https://stripe.com/docs/stripe-cli
2. In terminal: `stripe login`
3. In another terminal: `stripe listen --forward-to localhost:5000/webhook/stripe`
4. This gives you a webhook signing secret - use that in .env

### Testing Without Stripe CLI

For initial testing, you can manually test by:
1. Going through checkout
2. Checking if user status changed in database
3. Checking Flask logs for webhook attempts

---

## Verifying Setup

### Check 1: Imports Work

```bash
python -c "from app import app; print('✓ App imports successfully')"
```

Expected output:
```
Database path: /path/to/app.db
DATABASE URI: sqlite:///...
✓ App imports successfully
```

### Check 2: Payment Routes Exist

```bash
python -c "
from app import app
routes = [r.rule for r in app.url_map.iter_rules()]
payment_routes = [r for r in routes if 'payment' in r or 'checkout' in r or 'razorpay' in r or 'webhook' in r]
for r in payment_routes:
    print(r)
"
```

Expected output:
```
/create-checkout-session
/payment/success
/webhook/stripe
/create-razorpay-order
/verify-razorpay-payment
/pricing
```

### Check 3: Environment Variables Loaded

```bash
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('STRIPE_SECRET_KEY:', '✓' if os.getenv('STRIPE_SECRET_KEY') else '✗')
print('RAZORPAY_KEY_ID:', '✓' if os.getenv('RAZORPAY_KEY_ID') else '✗')
"
```

Expected output:
```
STRIPE_SECRET_KEY: ✓
RAZORPAY_KEY_ID: ✓
```

---

## Common Issues & Solutions

### Issue 1: "ModuleNotFoundError: No module named 'stripe'"

**Solution:**
```bash
pip install stripe razorpay requests
```

### Issue 2: Environment variables not loading

**Check:**
1. .env file exists in project root
2. .env file has correct format: `KEY=value`
3. No spaces around `=`: ✓ `STRIPE_SECRET_KEY=value` ✗ `STRIPE_SECRET_KEY = value`
4. Restart Flask after editing .env

**Debug:**
```bash
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print(os.getenv('STRIPE_SECRET_KEY'))
"
```

### Issue 3: Stripe test card declined

**Check:**
1. Using test mode keys (start with `sk_test_`)
2. Card number is exactly: `4242 4242 4242 4242`
3. Expiry is any future date
4. CVC is any 3 digits

### Issue 4: Razorpay payment returns "Key not found"

**Check:**
1. RAZORPAY_KEY_ID exists in .env
2. Key ID format: `rzp_test_xxxxx` (for test mode)
3. Key ID is copied correctly from dashboard
4. No extra spaces in .env

### Issue 5: Webhook not received by Flask

**Solutions:**
1. **For localhost:** Use Stripe CLI: `stripe listen --forward-to localhost:5000/webhook/stripe`
2. **For production:** Ensure:
   - URL is publicly accessible
   - HTTPS is enabled
   - No firewall blocking the port

### Issue 6: "Payment verification failed" in Razorpay

**Check:**
1. RAZORPAY_KEY_SECRET copied correctly
2. Order ID matches in request
3. Payment ID is from the same order
4. Signature matches expectation

**Debug:**
```bash
python -c "
import hmac
import hashlib
order_id = 'order_xxxxx'
payment_id = 'pay_xxxxx'
secret = 'YOUR_SECRET'
message = f'{order_id}|{payment_id}'
signature = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
print('Generated signature:', signature)
"
```

---

## Next Steps After Setup

1. **Test with real users:**
   - Create test user accounts
   - Go through complete payment flow
   - Verify premium features work

2. **Set up error notifications:**
   - Add logging for payment errors
   - Set up email alerts
   - Monitor webhook failures

3. **Configure for production:**
   - Switch to live API keys
   - Update webhook URLs
   - Enable HTTPS
   - Test with real payments

4. **Monitor payments:**
   - Check Stripe/Razorpay dashboards
   - Monitor database for premium users
   - Track payment failures

---

## Support Resources

- **Stripe Docs:** https://stripe.com/docs
- **Razorpay Docs:** https://razorpay.com/docs
- **Flask Payment Tutorials:** Search for "Flask Stripe" or "Flask Razorpay"
- **HMAC Verification:** https://en.wikipedia.org/wiki/HMAC

## Files Modified

1. **app.py** - Added payment routes and initialization
2. **requirements.txt** - Added stripe, razorpay, requests
3. **templates/pricing.html** - Already has payment buttons
4. **.env** - Create this file with API keys

## Testing Endpoints

Once setup is complete, test these URLs:

```
GET  /pricing                           - View pricing page
POST /create-checkout-session          - Create Stripe session
GET  /payment/success                  - Stripe success page
POST /webhook/stripe                   - Stripe webhook (automatic)
POST /create-razorpay-order            - Create Razorpay order
POST /verify-razorpay-payment          - Verify Razorpay payment
```
