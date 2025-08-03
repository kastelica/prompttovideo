"""
Database migration to add Phase 5 fields to Video model
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import Video

def upgrade():
    """Add new fields to Video table"""
    app = create_app()
    
    with app.app_context():
        # Add new columns to videos table
        with db.engine.connect() as conn:
            conn.execute(db.text("""
                ALTER TABLE videos 
                ADD COLUMN title VARCHAR(200)
            """))
            conn.execute(db.text("""
                ALTER TABLE videos 
                ADD COLUMN description TEXT
            """))
            conn.execute(db.text("""
                ALTER TABLE videos 
                ADD COLUMN tags JSON
            """))
            conn.execute(db.text("""
                ALTER TABLE videos 
                ADD COLUMN share_token VARCHAR(64)
            """))
            conn.execute(db.text("""
                ALTER TABLE videos 
                ADD COLUMN embed_enabled BOOLEAN DEFAULT TRUE
            """))
            conn.commit()
        
        print("✅ Added Phase 5 fields to videos table")

def downgrade():
    """Remove new fields from Video table"""
    app = create_app()
    
    with app.app_context():
        # Remove columns from videos table
        with db.engine.connect() as conn:
            conn.execute(db.text("ALTER TABLE videos DROP COLUMN title"))
            conn.execute(db.text("ALTER TABLE videos DROP COLUMN description"))
            conn.execute(db.text("ALTER TABLE videos DROP COLUMN tags"))
            conn.execute(db.text("ALTER TABLE videos DROP COLUMN share_token"))
            conn.execute(db.text("ALTER TABLE videos DROP COLUMN embed_enabled"))
            conn.commit()
        
        print("✅ Removed Phase 5 fields from videos table")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        upgrade() 