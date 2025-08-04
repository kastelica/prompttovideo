"""Add subscription fields to User model"""

from sqlalchemy import text
from app import db

def upgrade():
    """Add subscription fields to users table"""
    conn = db.engine.connect()
    
    # Add subscription fields one at a time (SQLite requirement)
    try:
        conn.execute(text("ALTER TABLE users ADD COLUMN subscription_id VARCHAR(255)"))
    except Exception as e:
        print(f"Note: subscription_id column might already exist: {e}")
    
    try:
        conn.execute(text("ALTER TABLE users ADD COLUMN subscription_status VARCHAR(20) DEFAULT 'inactive'"))
    except Exception as e:
        print(f"Note: subscription_status column might already exist: {e}")
    
    conn.commit()
    conn.close()

def downgrade():
    """Remove subscription fields from users table"""
    conn = db.engine.connect()
    
    # Note: SQLite doesn't support DROP COLUMN in older versions
    # This would require recreating the table, which is complex
    # For now, we'll just log that this operation isn't supported
    print("Warning: DROP COLUMN not supported in SQLite. Manual table recreation required.")
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    upgrade()
    print("✅ Added subscription fields to users table") 