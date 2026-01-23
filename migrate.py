from app import app, db
from sqlalchemy import text



with app.app_context():
    with db.engine.connect() as conn:
        # Add new columns
        try:
            conn.execute(text("ALTER TABLE user_daily_progress ADD COLUMN today_goal_names TEXT"))
            conn.execute(text("ALTER TABLE user_daily_progress ADD COLUMN last_evaluated_date DATE"))
            conn.execute(text("ALTER TABLE user_daily_progress ADD COLUMN total_goals_completed INTEGER DEFAULT 0"))
            conn.execute(text("ALTER TABLE user_daily_progress ADD COLUMN total_goals_attempted INTEGER DEFAULT 0"))
            conn.commit()
            print("✅ Migration successful!")
        except Exception as e:
            print(f"Migration note: {e}")





# migration_update_progress.py
# Run this script once to update your database schema

from app import app, db
from models.book import UserDailyProgress
from sqlalchemy import text

def migrate_database():
    """Migrate the UserDailyProgress table to new schema"""
    with app.app_context():
        try:
            # Check if we need to migrate
            print("Starting database migration...")
            
            # Add new columns if they don't exist
            with db.engine.connect() as conn:
                # Check current schema
                result = conn.execute(text("PRAGMA table_info(user_daily_progress)"))
                columns = {row[1] for row in result}
                
                print(f"Current columns: {columns}")
                
                # Add missing columns
                migrations = []
                
                if 'today_goal_names' not in columns:
                    migrations.append(
                        "ALTER TABLE user_daily_progress ADD COLUMN today_goal_names TEXT"
                    )
                
                if 'last_evaluated_date' not in columns:
                    migrations.append(
                        "ALTER TABLE user_daily_progress ADD COLUMN last_evaluated_date DATE"
                    )
                
                if 'total_goals_completed' not in columns:
                    migrations.append(
                        "ALTER TABLE user_daily_progress ADD COLUMN total_goals_completed INTEGER DEFAULT 0"
                    )
                
                if 'total_goals_attempted' not in columns:
                    migrations.append(
                        "ALTER TABLE user_daily_progress ADD COLUMN total_goals_attempted INTEGER DEFAULT 0"
                    )
                
                # Execute migrations
                for migration in migrations:
                    print(f"Executing: {migration}")
                    conn.execute(text(migration))
                    conn.commit()
                
                print(f"Added {len(migrations)} new columns")
            
            # Update existing records
            all_progress = UserDailyProgress.query.all()
            print(f"Updating {len(all_progress)} existing progress records...")
            
            for progress in all_progress:
                # Initialize new fields
                if not hasattr(progress, 'today_goal_names') or progress.today_goal_names is None:
                    progress.today_goal_names = []
                
                if not hasattr(progress, 'last_evaluated_date') or progress.last_evaluated_date is None:
                    progress.last_evaluated_date = progress.today_date
                
                if not hasattr(progress, 'total_goals_completed'):
                    progress.total_goals_completed = 0
                
                if not hasattr(progress, 'total_goals_attempted'):
                    progress.total_goals_attempted = 0
                
                # Ensure today_tasks is a list
                if progress.today_tasks is None:
                    progress.today_tasks = []
            
            db.session.commit()
            print("Migration completed successfully!")
            print("\nDatabase schema updated:")
            print("✓ Added today_goal_names column")
            print("✓ Added last_evaluated_date column")
            print("✓ Added total_goals_completed column")
            print("✓ Added total_goals_attempted column")
            print("✓ Updated existing records")
            
        except Exception as e:
            print(f"Migration failed: {e}")
            db.session.rollback()
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    migrate_database()