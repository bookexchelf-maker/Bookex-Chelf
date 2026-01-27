#!/usr/bin/env python
"""
Script to create a freemium test user (no premium) for Bookex Chelf
This version skips email verification for quick testing
"""





from models.book import User, Shelf, Book
from app import db

from app import app, db
from models.book import User, EmailVerificationOTP
from datetime import datetime

def create_freemium_user():
    """Create a freemium test user (free tier, no premium)"""
    with app.app_context():
        # Check if user already exists
        existing_user = User.query.filter_by(email="freemium@test.com").first()
        if existing_user:
            print("⚠️  User already exists!")
            print(f"Email: {existing_user.email}")
            print(f"Premium: {existing_user.is_premium}")
            return
        
        # Create new freemium user (free tier - not premium)
        freemium_user = User(
            name="Test User 2",
            email="freeuser@test.com"
        )
        freemium_user.set_password("12345678")
        freemium_user.is_premium = False  # Free tier user
        freemium_user.is_email_verified = True  # Mark as verified (skip email verification)
        freemium_user.email_verified_at = datetime.utcnow()
        
        db.session.add(freemium_user)
        db.session.commit()
        
        print("✅ Freemium test user created successfully!")
        print(f"\n📧 Email: freemium@test.com")
        print(f"🔑 Password: test1234")
        print(f"👤 Name: Freemium Test User")
        print(f"💎 Premium: No (Free tier)")
        print(f"✓ Email Verified: Yes")


def create_premium_user():
    """Create a premium test user for comparison"""
    with app.app_context():
        # Check if user already exists
        existing_user = User.query.filter_by(email="premium@test.com").first()
        if existing_user:
            print("⚠️  Premium user already exists!")
            print(f"Email: {existing_user.email}")
            print(f"Premium: {existing_user.is_premium}")
            return
        
        # Create new premium user
        from datetime import timedelta
        
        premium_user = User(
            name="Premium Test User",
            email="premium@test.com"
        )
        premium_user.set_password("test1234")
        premium_user.is_premium = True  # Premium tier user
        premium_user.premium_since = datetime.utcnow()
        premium_user.premium_until = datetime.utcnow() + timedelta(days=365)  # 1 year of premium
        premium_user.is_email_verified = True  # Mark as verified
        premium_user.email_verified_at = datetime.utcnow()
        
        db.session.add(premium_user)
        db.session.commit()
        
        print("✅ Premium test user created successfully!")
        print(f"\n📧 Email: premium@test.com")
        print(f"🔑 Password: test1234")
        print(f"👤 Name: Premium Test User")
        print(f"💎 Premium: Yes (365 days)")
        print(f"✓ Email Verified: Yes")


if __name__ == "__main__":
    import sys
    
    print("=" * 70)
    print("🚀 Bookex Chelf - Test User Creator")
    print("=" * 70 + "\n")
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "premium":
            print("Creating Premium Test User...\n")
            create_premium_user()
        elif sys.argv[1] == "freemium":
            print("Creating Freemium Test User...\n")
            create_freemium_user()
        elif sys.argv[1] == "both":
            print("Creating Both Test Users...\n")
            create_freemium_user()
            print("\n" + "-" * 70 + "\n")
            create_premium_user()
        else:
            print("❌ Unknown argument!")
            print("\nUsage:")
            print("  python create_test_user.py freemium    # Create freemium user only")
            print("  python create_test_user.py premium     # Create premium user only")
            print("  python create_test_user.py both        # Create both users")
            sys.exit(1)
    else:
        # Default: create both users
        print("Creating Both Test Users...\n")
        create_freemium_user()
        print("\n" + "-" * 70 + "\n")
        create_premium_user()
    
    print("\n" + "=" * 70)
    print("Ready for testing!")
    print("=" * 70)







