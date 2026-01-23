# Payment Processing Setup Guide

## Overview
Book Chelf supports two major payment gateways for premium subscription:

1. **Stripe** - For international card payments (credit/debit cards)
2. **Razorpay** - For Indian payments (UPI, card, netbanking, etc.)

## Architecture

### Payment Flow

```
User clicks "Upgrade to Premium" 
    ↓
Navigate to /pricing page
    ↓
Choose payment method:
  • Stripe (Card) → /create-checkout-session → Stripe Hosted Checkout
  • Razorpay (UPI/Card) → /create-razorpay-order → Razorpay Popup
    ↓
Complete payment on external gateway
    ↓
Payment verification (webhook or client-side verification)
    ↓
Update user.is_premium = True in database
    ↓
Redirect to /dashboard with premium access enabled
```

## Configuration

### Environment Variables (.env file)

Add these variables to your `.env` file in the project root:

```
# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_xxxxxxxxxxxxx
STRIPE_PUBLIC_KEY=pk_test_xxxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxx

# Razorpay Configuration
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxxx
RAZORPAY_KEY_SECRET=xxxxxxxxxxxxx
```

## Payment Providers Setup

### 1. Stripe Setup (International Payments)

#### Getting Your Keys:

1. **Create Stripe Account**
   - Go to https://dashboard.stripe.com
   - Sign up with your business email
   - Verify email

2. **Get API Keys**
   - Dashboard → Settings → API Keys
   - Copy "Secret Key" (starts with `sk_test_` for test mode)
   - Copy "Publishable Key" (starts with `pk_test_` for test mode)

3. **Set Up Webhook**
   - Dashboard → Settings → Webhooks
   - Click "Add endpoint"
   - URL: `https://yourdomain.com/webhook/stripe` (or use ngrok for local testing)
   - Events to listen:
     - `checkout.session.completed`
   - Copy the signing secret (starts with `whsec_`)

4. **Test Cards** (in test mode):
   - Visa: `4242 4242 4242 4242`
   - Any future expiry date
   - Any 3-digit CVC

### 2. Razorpay Setup (Indian Payments)

#### Getting Your Keys:

1. **Create Razorpay Account**
   - Go to https://razorpay.com
   - Sign up with your business details
   - Verify email and phone

2. **Get API Keys**
   - Dashboard → Settings → API Keys
   - Copy "Key ID" (looks like `rzp_test_xxxxx`)
   - Copy "Key Secret"

3. **Activate Payment Methods** (in Settings)
   - UPI
   - Cards
   - Netbanking
   - Wallets

4. **Test UPI ID** (in test mode):
   - Use: `success@razorpay` (to simulate success)
   - Use: `failed@razorpay` (to simulate failure)

## API Endpoints

### 1. Create Checkout Session (Stripe)

**Endpoint:** `POST /create-checkout-session`

**Request:**
```
(Automatically called by form submission)
```

**Response:**
```
Redirects to Stripe checkout page
```

**Flow:**
1. User clicks "Pay with Card (Stripe)" button
2. Form posts to this endpoint
3. Server creates a Stripe checkout session
4. User is redirected to Stripe's secure checkout page
5. After payment, Stripe redirects to success URL
6. Webhook handler updates user to premium

### 2. Create Razorpay Order

**Endpoint:** `POST /create-razorpay-order`

**Request:**
```json
{}
```

**Response:**
```json
{
  "order_id": "order_xxxxxxxxxxxxx",
  "amount": 29900,
  "currency": "INR",
  "key": "rzp_test_xxxxxxxxxxxxx"
}
```

**Flow:**
1. User clicks "Pay with UPI/Card (Razorpay)" button
2. JavaScript fetches this endpoint
3. Server creates a Razorpay order
4. Order details and API key returned to client
5. Razorpay popup opens on client-side
6. User completes payment in popup
7. Payment handler calls verification endpoint

### 3. Verify Razorpay Payment

**Endpoint:** `POST /verify-razorpay-payment`

**Request:**
```json
{
  "razorpay_payment_id": "pay_xxxxxxxxxxxxx",
  "razorpay_order_id": "order_xxxxxxxxxxxxx",
  "razorpay_signature": "signature_hash"
}
```

**Response (Success):**
```json
{
  "success": true,
  "message": "Premium activated successfully!"
}
```

**Response (Failure):**
```json
{
  "success": false,
  "error": "Payment verification failed"
}
```

**Security:**
- Signature verification using HMAC-SHA256
- Prevents payment tampering
- Only valid signatures are processed

### 4. Stripe Webhook Handler

**Endpoint:** `POST /webhook/stripe`

**Events Handled:**
- `checkout.session.completed` - Payment successful

**Process:**
1. Stripe sends webhook event
2. Signature verified using webhook secret
3. User marked as premium in database
4. No manual action needed - automatic

## Database Changes

### User Model Fields (already implemented)

```python
class User(db.Model):
    is_premium = db.Column(db.Boolean, default=False)
    premium_since = db.Column(db.DateTime)
    premium_until = db.Column(db.DateTime)
```

### After Successful Payment:

```
is_premium = True
premium_since = Current timestamp
premium_until = Current timestamp + 365 days
```

## Premium Features Gating

All premium-only features are protected by the `@premium_required` decorator:

```python
@app.route("/some-premium-route")
@login_required
@premium_required
def premium_feature():
    # Only accessible to premium users
    pass
```

## Testing Payments

### Using Stripe Test Cards

1. Amount: Use any amount (e.g., $4.99)
2. Card: `4242 4242 4242 4242`
3. Expiry: Any future date (e.g., 12/25)
4. CVC: Any 3 digits
5. Click "Complete payment"

### Using Razorpay Test UPI

1. Amount: Will be ₹299 (automatically set)
2. Choose UPI method
3. Enter: `success@razorpay` (for success)
4. Complete payment

## Pricing Configuration

**Monthly Premium: ₹299 (29900 paise)**

To change price, modify these values in app.py:

```python
# Stripe
'unit_amount': 29900,  # In cents (₹299)

# Razorpay
'amount': 29900,  # In paise (₹299)
```

## Troubleshooting

### "Payment gateway key not found"
- Add API keys to `.env` file
- Restart Flask application

### Stripe test card declined
- Ensure using test mode API keys (start with `sk_test_`)
- Check webhook endpoint is accessible

### Razorpay signature mismatch
- Verify `RAZORPAY_KEY_SECRET` matches dashboard
- Check order ID and payment ID in request
- Ensure secret is URL-decoded

### User not becoming premium after payment
- Check database for `is_premium` column
- Verify premium_until date is in future
- Check browser console for JavaScript errors

## Going Live

### Before Production:

1. **Get Live API Keys**
   - Switch to Live mode in payment provider dashboard
   - Replace test keys with live keys in `.env`

2. **Update URLs**
   - Set `FLASK_ENV=production`
   - Update webhook URLs to production domain
   - Remove test payment routes

3. **SSL/HTTPS**
   - All payment pages must be HTTPS
   - Required by Stripe and Razorpay

4. **Remove Debug Mode**
   - Remove `/upgrade/test` route for test premium activation
   - Remove test payment buttons

5. **Test End-to-End**
   - Test with real test cards
   - Test webhook delivery
   - Verify database updates

## Additional Resources

- **Stripe Docs:** https://stripe.com/docs
- **Razorpay Docs:** https://razorpay.com/docs
- **Flask-Stripe:** Community integration examples
- **HMAC Verification:** https://en.wikipedia.org/wiki/HMAC

## Support

For issues with:
- **Stripe:** https://stripe.com/support
- **Razorpay:** https://razorpay.com/support
- **Application:** Check logs and browser console errors
