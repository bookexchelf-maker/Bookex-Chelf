#!/usr/bin/env python
from app import app, db
from models.book import User

with app.app_context():
    # Try to query a user
    try:
        users = User.query.all()
        print(f"Total users in database: {len(users)}")
        
        if users:
            user = users[0]
            print(f"\nFirst user: {user.email}")
            print(f"User attributes:")
            print(f"  - id: {user.id}")
            print(f"  - name: {user.name}")
            print(f"  - email: {user.email}")
            print(f"  - is_premium: {user.is_premium if hasattr(user, 'is_premium') else 'NOT FOUND'}")
            print(f"  - last_login: {user.last_login if hasattr(user, 'last_login') else 'NOT FOUND'}")
            print(f"  - daily_time_spend: {user.daily_time_spend if hasattr(user, 'daily_time_spend') else 'NOT FOUND'}")
        
        # Check if columns exist
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('user')]
        print(f"\nUser table columns: {columns}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
