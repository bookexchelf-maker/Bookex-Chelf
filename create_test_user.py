#!/usr/bin/env python
"""
Script to create a freemium test user for Bookex Chelf
"""

from app import app, db
from models.book import User

def create_freemium_test_user():
    """Create a freemium test user"""
    with app.app_context():
        # Check if test user already exists
        existing_user = User.query.filter_by(email="freemium@test.com").first()
        
        if existing_user:
            print(f"✓ Freemium test user already exists!")
            print(f"  Email: {existing_user.email}")
            print(f"  Name: {existing_user.name}")
            print(f"  Premium: {existing_user.is_premium}")
            return
        
        # Create new freemium user (free tier - not premium)
        test_user = User(
            name="Freemium Test User",
            email="freemium@test.com"
        )
        test_user.set_password("password123")  # Simple password for testing
        test_user.is_premium = False  # Free tier user
        
        db.session.add(test_user)
        db.session.commit()
        
        print("✅ Freemium test user created successfully!")
        print(f"  Email: freemium@test.com")
        print(f"  Password: password123")
        print(f"  Name: Freemium Test User")
        print(f"  Premium Status: ❌ Free (not premium)")
        print(f"  User ID: {test_user.id}")
        print("\n📖 Features available in FREE tier:")
        print("  • Up to 10 books")
        print("  • Up to 3 shelves")
        print("  • Basic reading tracker")
        print("  • Daily goals")
        print("  • File uploads")

def create_premium_test_user():
    """Create a premium test user"""
    from datetime import datetime, timedelta
    
    with app.app_context():
        # Check if test user already exists
        existing_user = User.query.filter_by(email="premium@test.com").first()
        
        if existing_user:
            print(f"\n✓ Premium test user already exists!")
            print(f"  Email: {existing_user.email}")
            print(f"  Name: {existing_user.name}")
            print(f"  Premium: {existing_user.is_premium}")
            print(f"  Premium Until: {existing_user.premium_until}")
            return
        
        # Create new premium user
        test_user = User(
            name="Premium Test User",
            email="premium@test.com"
        )
        test_user.set_password("password123")
        test_user.is_premium = True  # Premium user
        test_user.premium_since = datetime.utcnow()
        test_user.premium_until = datetime.utcnow() + timedelta(days=365)  # 1 year premium
        
        db.session.add(test_user)
        db.session.commit()
        
        print("\n✅ Premium test user created successfully!")
        print(f"  Email: premium@test.com")
        print(f"  Password: password123")
        print(f"  Name: Premium Test User")
        print(f"  Premium Status: ✅ Premium (paid)")
        print(f"  Premium Until: {test_user.premium_until.strftime('%Y-%m-%d')}")
        print(f"  User ID: {test_user.id}")
        print("\n🎉 Features available in PREMIUM tier:")
        print("  • Unlimited books & shelves")
        print("  • Advanced analytics")
        print("  • PDF annotation")
        print("  • Data export")
        print("  • Custom themes")
        print("  • Priority support")

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Bookex Chelf - Test User Creation")
    print("=" * 60)
    
    # Create both test users
    create_freemium_test_user()
    create_premium_test_user()
    
    print("\n" + "=" * 60)
    print("✅ Test users ready for testing!")
    print("=" * 60)
