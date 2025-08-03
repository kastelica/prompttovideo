"""
Migration to add thumbnail fields to videos table
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from sqlalchemy import text

def migrate():
    """Add thumbnail fields to videos table"""
    app = create_app()
    
    with app.app_context():
        try:
            # For SQLite, we'll just try to add the columns and catch the error if they exist
            try:
                print("Adding thumbnail_gcs_url column...")
                db.session.execute(text("""
                    ALTER TABLE videos 
                    ADD COLUMN thumbnail_gcs_url VARCHAR(2000)
                """))
                print("✅ Added thumbnail_gcs_url column")
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    print("ℹ️ thumbnail_gcs_url column already exists")
                else:
                    raise e
            
            try:
                print("Adding thumbnail_url column...")
                db.session.execute(text("""
                    ALTER TABLE videos 
                    ADD COLUMN thumbnail_url VARCHAR(2000)
                """))
                print("✅ Added thumbnail_url column")
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    print("ℹ️ thumbnail_url column already exists")
                else:
                    raise e
            
            db.session.commit()
            print("🎉 Migration completed successfully!")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    migrate() 