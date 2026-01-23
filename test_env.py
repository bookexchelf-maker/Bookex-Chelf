import os
from dotenv import load_dotenv

# Load .env
load_dotenv()

# Check what we got
key_id = os.getenv('RAZORPAY_KEY_ID')
key_secret = os.getenv('RAZORPAY_KEY_SECRET')

print('RAZORPAY_KEY_ID:', repr(key_id))
print('RAZORPAY_KEY_SECRET:', repr(key_secret))
print('')

if key_id and 'rzp_test' in key_id:
    print('✓ Key ID looks correct!')
else:
    print('✗ Key ID issue')

if key_secret and len(key_secret) > 10:
    print('✓ Key Secret looks correct!')
else:
    print('✗ Key Secret issue')
