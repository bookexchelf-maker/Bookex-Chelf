"""
Migration to fix Shelf.user_id type from VARCHAR to INTEGER
This addresses the Neon database schema issue where user_id was stored as text but needs to be integer
"""

import os
import sys

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ DATABASE_URL environment variable not set!")
    print("Please set DATABASE_URL in your .env file or environment")
    sys.exit(1)

# Convert postgresql:// to postgresql+psycopg2:// if needed
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

from sqlalchemy import create_engine, text

def migrate_shelf_user_id():
    """Migrate shelf table user_id from VARCHAR to INTEGER"""
    try:
        print("Starting Shelf table migration...")
        print(f"Connecting to database...")
        
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            # PostgreSQL migration: Convert shelf.user_id from VARCHAR to INTEGER
            print("Converting shelf.user_id from VARCHAR to INTEGER...")
            
            # Step 1: Drop the foreign key constraint
            conn.execute(text("""
                ALTER TABLE shelf 
                DROP CONSTRAINT IF EXISTS shelf_user_id_fkey
            """))
            conn.commit()
            print("✓ Dropped old foreign key constraint")
            
            # Step 2: Convert the column type (PostgreSQL can handle this if values are numeric)
            conn.execute(text("""
                ALTER TABLE shelf 
                ALTER COLUMN user_id TYPE INTEGER USING user_id::INTEGER
            """))
            conn.commit()
            print("✓ Converted user_id column to INTEGER")
            
            # Step 3: Add back the foreign key constraint
            conn.execute(text("""
                ALTER TABLE shelf 
                ADD CONSTRAINT shelf_user_id_fkey 
                FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE
            """))
            conn.commit()
            print("✓ Added new foreign key constraint")
            
            print("\n✅ Shelf table migration completed successfully!")
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    migrate_shelf_user_id()
