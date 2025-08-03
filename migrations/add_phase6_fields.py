#!/usr/bin/env python3
"""
Migration script to add Phase 6 fields for queue prioritization, rate limiting, and analytics
"""
import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from sqlalchemy import text

def upgrade():
    """Add Phase 6 fields to the database"""
    app = create_app()
    
    with app.app_context():
        # Add fields to videos table
        with db.engine.connect() as conn:
            # Check if columns exist before adding them
            result = conn.execute(text("PRAGMA table_info(videos)"))
            existing_columns = [row[1] for row in result.fetchall()]
            
            # Add priority field if it doesn't exist
            if 'priority' not in existing_columns:
                conn.execute(text("ALTER TABLE videos ADD COLUMN priority INTEGER DEFAULT 0"))
            
            # Add queued_at field if it doesn't exist
            if 'queued_at' not in existing_columns:
                conn.execute(text("ALTER TABLE videos ADD COLUMN queued_at DATETIME DEFAULT CURRENT_TIMESTAMP"))
            
            # Add started_at field if it doesn't exist
            if 'started_at' not in existing_columns:
                conn.execute(text("ALTER TABLE videos ADD COLUMN started_at DATETIME"))
            
            # Check users table columns
            result = conn.execute(text("PRAGMA table_info(users)"))
            existing_user_columns = [row[1] for row in result.fetchall()]
            
            # Add fields to users table if they don't exist
            if 'api_calls_today' not in existing_user_columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN api_calls_today INTEGER DEFAULT 0 NOT NULL"))
            
            if 'last_api_call' not in existing_user_columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN last_api_call DATETIME"))
            
            if 'subscription_tier' not in existing_user_columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN subscription_tier VARCHAR(20) DEFAULT 'free'"))
            
            # Check if api_usage table exists
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='api_usage'"))
            if not result.fetchone():
                # Create api_usage table
                conn.execute(text("""
                    CREATE TABLE api_usage (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        endpoint VARCHAR(100) NOT NULL,
                        method VARCHAR(10) NOT NULL,
                        response_time FLOAT,
                        status_code INTEGER,
                        user_agent VARCHAR(500),
                        ip_address VARCHAR(45),
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                """))
            
            # Check if indexes exist before creating them
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='index'"))
            existing_indexes = [row[0] for row in result.fetchall()]
            
            # Create indexes for better performance if they don't exist
            if 'idx_videos_priority' not in existing_indexes:
                conn.execute(text("CREATE INDEX idx_videos_priority ON videos (priority DESC)"))
            
            if 'idx_videos_status_priority' not in existing_indexes:
                conn.execute(text("CREATE INDEX idx_videos_status_priority ON videos (status, priority DESC)"))
            
            if 'idx_api_usage_user_date' not in existing_indexes:
                conn.execute(text("CREATE INDEX idx_api_usage_user_date ON api_usage (user_id, created_at)"))
            
            if 'idx_api_usage_endpoint' not in existing_indexes:
                conn.execute(text("CREATE INDEX idx_api_usage_endpoint ON api_usage (endpoint)"))
            
            conn.commit()
        
        print("Phase 6 migration completed successfully!")

def downgrade():
    """Remove Phase 6 fields from the database"""
    app = create_app()
    
    with app.app_context():
        with db.engine.connect() as conn:
            # Remove indexes
            conn.execute(text("DROP INDEX IF EXISTS idx_videos_priority"))
            conn.execute(text("DROP INDEX IF EXISTS idx_videos_status_priority"))
            conn.execute(text("DROP INDEX IF EXISTS idx_api_usage_user_date"))
            conn.execute(text("DROP INDEX IF EXISTS idx_api_usage_endpoint"))
            
            # Drop api_usage table
            conn.execute(text("DROP TABLE IF EXISTS api_usage"))
            
            # Remove fields from videos table
            conn.execute(text("ALTER TABLE videos DROP COLUMN priority"))
            conn.execute(text("ALTER TABLE videos DROP COLUMN queued_at"))
            conn.execute(text("ALTER TABLE videos DROP COLUMN started_at"))
            
            # Remove fields from users table
            conn.execute(text("ALTER TABLE users DROP COLUMN api_calls_today"))
            conn.execute(text("ALTER TABLE users DROP COLUMN last_api_call"))
            conn.execute(text("ALTER TABLE users DROP COLUMN subscription_tier"))
            
            conn.commit()
        
        print("Phase 6 migration rolled back successfully!")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'downgrade':
        downgrade()
    else:
        upgrade() 