# Payment System - Quick Reference

## Payment Flow Summary

```
USER JOURNEY:
1. User clicks "Upgrade to Premium" link
   ↓
2. Redirected to /pricing page
   ↓
3. User chooses payment method:
   
   A) STRIPE FLOW:
      Click "💳 Pay with Card (Stripe)"
      ↓ Form submits to POST /create-checkout-session
      ↓ Stripe checkout page opens
      ↓ User enters card details
      ↓ Payment processed by Stripe
      ↓ Webhook /webhook/stripe confirms payment
      ↓ User marked premium in database
      ↓ (Optional) Manual check on /payment/success
   
   B) RAZORPAY FLOW:
      Click "🇮🇳 Pay with UPI/Card (Razorpay)"
      ↓ JavaScript fetches POST /create-razorpay-order
      ↓ Razorpay popup appears
      ↓ User selects UPI/Card method
      ↓ User completes payment
      ↓ JavaScript fetches POST /verify-razorpay-payment
      ↓ Signature verified on server
      ↓ User marked premium in database
      ↓ Redirected to /dashboard
```

## Available Endpoints

### 1. GET /pricing
- **Purpose:** Display pricing page with payment options
- **Auth Required:** No (shows login prompt if not logged in)
- **Returns:** Pricing page HTML with payment buttons
- **User Flow:** This is where user lands to choose payment method

### 2. POST /create-checkout-session
- **Purpose:** Create Stripe payment session
- **Auth Required:** Yes (login_required decorator)
- **Method:** Form submission (from Stripe button)
- **Returns:** Redirect to Stripe checkout URL
- **Payment Gateway:** Stripe
- **Amount:** ₹299 (₹299.00 charged to card)

**Frontend:**
```html
<form action="/create-checkout-session" method="POST">
  <button type="submit" class="btn-upgrade">
    💳 Pay with Card (Stripe)
  </button>
</form>
```

### 3. POST /create-razorpay-order
- **Purpose:** Create Razorpay order for UPI/card payment
- **Auth Required:** Yes (session user_id required)
- **Method:** AJAX (JavaScript fetch)
- **Content-Type:** application/json
- **Request Body:** Empty JSON `{}`
- **Returns:** JSON with order details
- **Response:**
```json
{
  "order_id": "order_xxxxxxxxxxxxx",
  "amount": 29900,
  "currency": "INR",
  "key": "rzp_test_xxxxxxxxxxxxx"
}
```

**Frontend (JavaScript):**
```javascript
document.getElementById('razorpay-btn').addEventListener('click', async function() {
    const response = await fetch('/create-razorpay-order', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: '{}'
    });
    const data = await response.json();
    // Open Razorpay popup with data
});
```

### 4. POST /verify-razorpay-payment
- **Purpose:** Verify Razorpay payment signature and activate premium
- **Auth Required:** Yes (session user_id required)
- **Method:** AJAX (JavaScript fetch)
- **Content-Type:** application/json
- **Request Body:**
```json
{
  "razorpay_payment_id": "pay_xxxxxxxxxxxxx",
  "razorpay_order_id": "order_xxxxxxxxxxxxx",
  "razorpay_signature": "signature_hash_xxxxx"
}
```

**Returns (Success):**
```json
{
  "success": true,
  "message": "Premium activated successfully!"
}
```

**Returns (Failure):**
```json
{
  "success": false,
  "error": "Payment verification failed"
}
```

**Frontend (JavaScript):**
```javascript
const response = await fetch('/verify-razorpay-payment', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        razorpay_payment_id: response.razorpay_payment_id,
        razorpay_order_id: response.razorpay_order_id,
        razorpay_signature: response.razorpay_signature
    })
});
const result = await response.json();
if (result.success) {
    window.location.href = '/dashboard';  // Redirect to dashboard
}
```

### 5. POST /webhook/stripe
- **Purpose:** Handle Stripe webhook events (asynchronous)
- **Auth Required:** No (webhook signature verification)
- **Method:** POST (from Stripe servers)
- **Content-Type:** application/json
- **Signature Verification:** Required (via Stripe-Signature header)
- **Handles Event:** `checkout.session.completed`

**What Happens:**
1. Stripe sends webhook when payment succeeds
2. Server verifies webhook signature
3. User is marked premium
4. No client-side action needed

### 6. GET /payment/success
- **Purpose:** Success page after Stripe payment
- **Auth Required:** Yes
- **Returns:** Confirmation message and redirect to dashboard
- **Note:** Optional - Stripe can redirect directly to dashboard

## Database Updates

### Before Payment:
```python
user.is_premium = False
user.premium_since = None
user.premium_until = None
```

### After Successful Payment:
```python
user.is_premium = True
user.premium_since = <current_datetime>
user.premium_until = <current_datetime + 365 days>
```

## Environment Variables Required

```bash
# Stripe
STRIPE_SECRET_KEY=sk_test_xxxxxxxxxxxxx
STRIPE_PUBLIC_KEY=pk_test_xxxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxx

# Razorpay
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxxx
RAZORPAY_KEY_SECRET=xxxxxxxxxxxxx
```

## Error Scenarios

### Scenario 1: User Not Logged In
- Stripe: Redirects to login via `@login_required`
- Razorpay: Returns 401 error "User not found"

### Scenario 2: Invalid Razorpay Signature
- Returns 400 error "Payment verification failed"
- User NOT marked premium
- User should retry payment

### Scenario 3: Network Error During Razorpay Verification
- JavaScript catch block handles it
- Error alert shown to user
- User can retry

### Scenario 4: Stripe Webhook Fails
- Payment still completes on Stripe's end
- User should check /payment/success manually
- Or retry the payment

## Testing

### Stripe (test mode):
- Card: `4242 4242 4242 4242`
- Expiry: Any future date
- CVC: Any 3 digits

### Razorpay (test mode):
- UPI ID: `success@razorpay` (to succeed)
- UPI ID: `failed@razorpay` (to fail)

## Complete Payment Process Timeline

```
T=0s   User clicks "Upgrade to Premium" → /pricing page loads
T=5s   User selects payment method
       
       RAZORPAY PATH:
T=6s   POST /create-razorpay-order
T=6.5s Response: {order_id, amount, key}
T=7s   Razorpay popup opens
T=20s  User enters UPI ID and confirms
T=25s  Razorpay returns payment_id and signature
T=26s  POST /verify-razorpay-payment
T=26.5s Server verifies signature ✓
T=27s  user.is_premium = True (database updated)
T=27.5s Response: {success: true}
T=28s  JavaScript redirects to /dashboard
T=30s  User sees "🎉 Premium features unlocked!"

       STRIPE PATH:
T=6s   POST /create-checkout-session
T=6.5s Redirect to Stripe checkout
T=7s   Stripe payment page loads
T=30s  User enters card and pays
T=35s  Stripe redirects to /payment/success
T=40s  (Webhook arrives asynchronously)
T=40.5s user.is_premium = True (database updated)
T=45s  User sees /dashboard with premium status
```

## Key Security Features

1. **Stripe Signature Verification**
   - Webhook requests signed with HMAC-SHA256
   - Server verifies signature matches

2. **Razorpay HMAC Verification**
   - Payment verification signed with key secret
   - Signature verified using HMAC-SHA256
   - Prevents payment tampering

3. **Session Authentication**
   - All endpoints check `session['user_id']`
   - Cannot process payment without login

4. **Database Atomic Transactions**
   - Premium status update wrapped in transaction
   - Ensures consistency

## Files Modified

1. **app.py**
   - Added imports: stripe, razorpay, hmac, hashlib
   - Added payment initialization
   - Added 5 payment endpoints

2. **requirements.txt**
   - Added: stripe, razorpay, requests

3. **templates/pricing.html**
   - Already has payment buttons and JavaScript
   - Receives Razorpay key from backend

4. **.env file (you create)**
   - Add payment API keys here
