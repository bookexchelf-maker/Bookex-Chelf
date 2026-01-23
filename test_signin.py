#!/usr/bin/env python
"""Test signin flow"""
import requests
from urllib.parse import urljoin

BASE_URL = "http://127.0.0.1:5000"

# Start with signin page to get session
session = requests.Session()

# Get signin page
print("Getting signin page...")
response = session.get(urljoin(BASE_URL, "/signin"))
print(f"Signin page status: {response.status_code}")

# Try signin with test credentials
print("\nAttempting signin...")
signin_data = {
    "email": "test@example.com",
    "password": "testpassword123"
}

response = session.post(
    urljoin(BASE_URL, "/signin"),
    data=signin_data,
    allow_redirects=True
)

print(f"Response status: {response.status_code}")
print(f"Final URL: {response.url}")

if "dashboard" in response.url:
    print("✓ SUCCESS: Redirected to dashboard!")
elif "signin" in response.url:
    print("✗ FAILED: Still on signin page")
    if "error" in response.text:
        print("  Error message may be in response")
else:
    print(f"✗ FAILED: Redirected to unexpected page: {response.url}")

# Check session
print(f"\nSession cookies: {session.cookies}")
print(f"Session user_id: {session.cookies.get('user_id', 'Not set')}")
