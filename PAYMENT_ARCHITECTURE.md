# Book Chelf Payment System - Technical Architecture

## Complete System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      BOOK CHELF APPLICATION                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐         ┌──────────────────────────┐     │
│  │  USER DASHBOARD  │         │   PRICING PAGE (/pricing)│     │
│  │                  │────────→│  - Free Plan display     │     │
│  │  "Upgrade Now"   │         │  - Premium Plan display  │     │
│  │     Button       │         │  - Payment buttons       │     │
│  └──────────────────┘         └──────────────────────────┘     │
│                                        ├─────────────────────┐  │
│                                        ↓                     ↓  │
│                               ┌─────────────────┐  ┌──────────────┐
│                               │ STRIPE BUTTON   │  │ RAZORPAY BTN  │
│                               └─────────────────┘  └──────────────┘
│                                        │                     │
│                                        ↓                     ↓
└────────────────────────────────────────┼─────────────────────┼────
                                         │                     │
                              ┌──────────────────────────────┐ │
                              │   FLASK APPLICATION          │ │
                              │ (app.py - Payment Routes)    │ │
                              └──────────────────────────────┘ │
                                         │                     │
                          ┌──────────────┘                     │
                          ↓                                    ↓
                 ┌──────────────────┐              ┌────────────────────┐
                 │  POST /create-   │              │ POST /create-      │
                 │  checkout-       │              │ razorpay-order     │
                 │  session         │              │                    │
                 │                  │              │ Returns:           │
                 │ Creates Stripe   │              │ - order_id         │
                 │ session          │              │ - amount           │
                 │                  │              │ - key (API Key)    │
                 └──────────────────┘              └────────────────────┘
                          │                                │
                          ↓                                ↓
         ┌────────────────────────────┐    ┌─────────────────────────┐
         │  STRIPE SERVERS            │    │  RAZORPAY SERVERS       │
         │  (Payment Processing)       │    │  (Payment Processing)   │
         │                            │    │                         │
         │  checkout.stripe.com       │    │  checkout.razorpay.com  │
         │  - Displays card form      │    │  - Displays UPI/Card    │
         │  - Processes payment       │    │  - Processes payment    │
         │  - Returns session ID      │    │  - Returns payment ID   │
         └────────────────────────────┘    └─────────────────────────┘
                          │                                │
                          ↓                                ↓
         ┌────────────────────────────┐    ┌─────────────────────────┐
         │  WEBHOOK /webhook/stripe   │    │ POST /verify-razorpay-  │
         │  (Asynchronous)            │    │ payment                 │
         │                            │    │ (Client→Server Direct)  │
         │  Stripe → Server           │    │                         │
         │  Triggers automatically    │    │ JavaScript sends:       │
         │  after payment success     │    │ - payment_id            │
         │  Signature verified        │    │ - order_id              │
         │  (HMAC-SHA256)            │    │ - signature             │
         └────────────────────────────┘    └─────────────────────────┘
                          │                                │
                          │         ┌──────────────────────┘
                          │         │
                          └────────→│
                                   ↓
         ┌─────────────────────────────────────┐
         │  PAYMENT VERIFICATION               │
         │  - Signature verified (HMAC-SHA256) │
         │  - Amount matched                   │
         │  - User ID retrieved                │
         │  - Status: VERIFIED ✓               │
         └─────────────────────────────────────┘
                          │
                          ↓
         ┌─────────────────────────────────────┐
         │  DATABASE UPDATE                    │
         │                                     │
         │  UPDATE User SET:                   │
         │  - is_premium = True                │
         │  - premium_since = NOW()            │
         │  - premium_until = NOW() + 365days  │
         │                                     │
         │  Status: COMMITTED ✓                │
         └─────────────────────────────────────┘
                          │
                          ↓
         ┌─────────────────────────────────────┐
         │  RESPONSE TO CLIENT                 │
         │                                     │
         │  JSON: {success: true}              │
         │  OR                                 │
         │  Redirect to /dashboard             │
         └─────────────────────────────────────┘
                          │
                          ↓
         ┌─────────────────────────────────────┐
         │  DASHBOARD REFRESH                  │
         │  - Show premium badge ⭐             │
         │  - Enable premium features          │
         │  - Update UI accordingly            │
         │                                     │
         │  User now has PREMIUM access! 🎉    │
         └─────────────────────────────────────┘
```

## Detailed Flow Comparison

### STRIPE PAYMENT FLOW

```
START
  │
  ├─→ User clicks "Pay with Card (Stripe)"
  │
  ├─→ Form POST to /create-checkout-session
  │
  ├─→ Flask creates stripe.checkout.Session
  │   Parameters:
  │   - Amount: 29900 paise (₹299)
  │   - Currency: INR
  │   - user_id: metadata
  │
  ├─→ Redirect to checkout.stripe.com
  │
  ├─→ User fills card details on Stripe
  │   (Secure - never touches your server)
  │
  ├─→ Stripe processes payment
  │
  ├─→ Stripe sends webhook POST to /webhook/stripe
  │   Webhook includes:
  │   - Event type: "checkout.session.completed"
  │   - Session ID
  │   - Metadata (user_id)
  │   - Signature (HMAC-SHA256)
  │
  ├─→ Flask verifies webhook signature
  │   Using: STRIPE_WEBHOOK_SECRET
  │
  ├─→ Signature valid? YES
  │   ├─→ Extract user_id from metadata
  │   ├─→ Update database:
  │   │   user.is_premium = True
  │   │   user.premium_since = NOW()
  │   │   user.premium_until = NOW() + 365 days
  │   ├─→ Return 200 OK
  │   │
  │   NO
  │   └─→ Return 400 "Invalid signature"
  │
  ├─→ (User sees success page at /payment/success)
  │   OR redirected to /dashboard
  │
  └─→ END - User has premium access ✓
```

### RAZORPAY PAYMENT FLOW

```
START
  │
  ├─→ User clicks "Pay with UPI/Card (Razorpay)"
  │
  ├─→ JavaScript fetch POST to /create-razorpay-order
  │
  ├─→ Flask creates razorpay Order
  │   razorpay_client.order.create({
  │     amount: 29900,        # ₹299 in paise
  │     currency: "INR",
  │     receipt: f"premium_{user.id}"
  │   })
  │
  ├─→ Flask returns JSON response:
  │   {
  │     order_id: "order_xxxxx",
  │     amount: 29900,
  │     currency: "INR",
  │     key: "rzp_test_xxxxx"  ← Razorpay API key
  │   }
  │
  ├─→ JavaScript opens Razorpay popup
  │   var options = {
  │     key: data.key,
  │     amount: data.amount,
  │     order_id: data.order_id,
  │     handler: function(response) { ... }
  │   }
  │   var rzp = new Razorpay(options);
  │   rzp.open();
  │
  ├─→ User selects payment method:
  │   - UPI
  │   - Credit/Debit Card
  │   - Netbanking
  │   - Wallet
  │
  ├─→ User completes payment on Razorpay
  │
  ├─→ Razorpay popup returns:
  │   {
  │     razorpay_payment_id: "pay_xxxxx",
  │     razorpay_order_id: "order_xxxxx",
  │     razorpay_signature: "signature_hash"
  │   }
  │
  ├─→ JavaScript handler calls:
  │   fetch POST to /verify-razorpay-payment
  │   body: { payment_id, order_id, signature }
  │
  ├─→ Flask verifies signature:
  │   message = f"{order_id}|{payment_id}"
  │   generated = HMAC-SHA256(message, KEY_SECRET)
  │   if (generated == razorpay_signature):
  │       ✓ Signature valid
  │   else:
  │       ✗ Signature invalid - REJECT payment
  │
  ├─→ Signature valid? YES
  │   ├─→ Update database:
  │   │   user.is_premium = True
  │   │   user.premium_since = NOW()
  │   │   user.premium_until = NOW() + 365 days
  │   ├─→ Return JSON: {success: true}
  │   │
  │   NO
  │   └─→ Return JSON: {success: false, error: "..."}
  │
  ├─→ JavaScript checks response.success
  │   if (success):
  │       window.location.href = '/dashboard'  ✓
  │   else:
  │       alert("Payment failed!")  ✗
  │
  ├─→ User redirected to /dashboard
  │
  └─→ END - User has premium access ✓
```

## Security Features

### 1. Stripe Webhook Verification
```
┌─────────────────────────────────────┐
│ Stripe sends webhook with signature │
├─────────────────────────────────────┤
│ verify = stripe.Webhook.construct_  │
│          event(payload, sig_header,  │
│          webhook_secret)             │
├─────────────────────────────────────┤
│ If signature valid:                 │
│   Process payment ✓                 │
│ If signature invalid:               │
│   Reject event ✗                    │
│   Potential attack detected!        │
└─────────────────────────────────────┘
```

### 2. Razorpay HMAC-SHA256 Verification
```
┌──────────────────────────────────────┐
│ Client sends payment response        │
├──────────────────────────────────────┤
│ Server reconstructs message:         │
│ message = "{order_id}|{payment_id}"  │
│                                      │
│ Server computes HMAC:                │
│ generated = HMAC-SHA256(             │
│     message,                         │
│     RAZORPAY_KEY_SECRET              │
│ )                                    │
├──────────────────────────────────────┤
│ if (generated == client_signature):  │
│   Signature valid ✓                  │
│   Update database                    │
│ else:                                │
│   Signature invalid ✗                │
│   Reject payment                     │
│   Possible tampering!                │
└──────────────────────────────────────┘
```

## Database Schema

### User Table (Premium Fields)

```
┌─────────────────────────────────────────┐
│ User                                    │
├─────────────────────────────────────────┤
│ id (PK)                                 │
│ email                                   │
│ password_hash                           │
│ name                                    │
│ ...                                     │
│ is_premium (Boolean, default False)     │
│ premium_since (DateTime, nullable)      │
│ premium_until (DateTime, nullable)      │
├─────────────────────────────────────────┤
│ Example Free User:                      │
│ is_premium: False                       │
│ premium_since: NULL                     │
│ premium_until: NULL                     │
│                                         │
│ Example Premium User:                   │
│ is_premium: True                        │
│ premium_since: 2024-01-19 10:30:00     │
│ premium_until: 2025-01-19 10:30:00     │
└─────────────────────────────────────────┘
```

## Integration Points

### Frontend Integration

```
templates/pricing.html
├─→ Stripe Button
│  └─→ <form action="/create-checkout-session" method="POST">
│
└─→ Razorpay Button
   └─→ <script> fetch("/create-razorpay-order")
       └─→ Opens Razorpay popup
       └─→ fetch("/verify-razorpay-payment")
```

### Backend Integration

```
app.py
├─→ Imports:
│  ├─→ import stripe
│  ├─→ import razorpay
│  ├─→ import hmac
│  └─→ import hashlib
│
├─→ Configuration:
│  ├─→ stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
│  └─→ razorpay_client = razorpay.Client(...)
│
└─→ Routes:
   ├─→ POST /create-checkout-session
   ├─→ GET /payment/success
   ├─→ POST /webhook/stripe
   ├─→ POST /create-razorpay-order
   └─→ POST /verify-razorpay-payment
```

### Environment Variables

```
.env file
├─→ Stripe
│  ├─→ STRIPE_SECRET_KEY
│  ├─→ STRIPE_PUBLIC_KEY
│  └─→ STRIPE_WEBHOOK_SECRET
│
└─→ Razorpay
   ├─→ RAZORPAY_KEY_ID
   └─→ RAZORPAY_KEY_SECRET
```

## Premium Feature Gating

```
@app.route("/premium-feature")
@login_required
@premium_required  ← Checks user.is_premium
def premium_feature():
    # Only accessible if:
    # 1. User is logged in
    # 2. user.is_premium == True
    # 3. user.premium_until > NOW()
    pass
```

## Testing Environment

```
┌──────────────────────────────────────┐
│  LOCAL TESTING SETUP                 │
├──────────────────────────────────────┤
│  Stripe Test Mode:                   │
│  - API Keys start with sk_test_      │
│  - Webhook Secret: whsec_test_       │
│  - Test Card: 4242 4242 4242 4242    │
│  - No real charges                   │
│                                      │
│  Razorpay Test Mode:                 │
│  - API Keys start with rzp_test_     │
│  - Test UPI: success@razorpay        │
│  - Test UPI: failed@razorpay         │
│  - No real charges                   │
└──────────────────────────────────────┘
```

## Production Checklist

```
☐ Stripe Live API Keys configured
☐ Razorpay Live API Keys configured
☐ HTTPS enabled on all pages
☐ Webhook URLs updated to production domain
☐ Database backed up
☐ Test payment end-to-end
☐ Error logging configured
☐ Email notifications configured
☐ Remove debug/test routes
☐ Security headers configured
☐ Rate limiting configured
☐ Monitor webhook delivery
```
