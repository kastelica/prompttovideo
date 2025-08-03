#!/usr/bin/env python3
"""
Migration script for Phase 7 features:
- Referrals table
- Additional fields for referral system
"""

from app import create_app, db
from sqlalchemy import text

def upgrade():
    app = create_app()
    with app.app_context():
        with db.engine.connect() as conn:
            # Check and create referrals table
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='referrals'"))
            if not result.fetchone():
                conn.execute(text("""
                    CREATE TABLE referrals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        referrer_id INTEGER NOT NULL,
                        referred_id INTEGER NOT NULL,
                        referrer_code VARCHAR(10) NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (referrer_id) REFERENCES users (id),
                        FOREIGN KEY (referred_id) REFERENCES users (id)
                    )
                """))
                
                # Create indexes for referrals table
                conn.execute(text("CREATE INDEX idx_referrals_referrer ON referrals (referrer_id)"))
                conn.execute(text("CREATE INDEX idx_referrals_referred ON referrals (referred_id)"))
                conn.execute(text("CREATE INDEX idx_referrals_code ON referrals (referrer_code)"))
            
            # Check and create indexes for existing tables if they don't exist
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='index'"))
            existing_indexes = [row[0] for row in result.fetchall()]
            
            if 'idx_users_referral_code' not in existing_indexes:
                conn.execute(text("CREATE INDEX idx_users_referral_code ON users (referral_code)"))
            if 'idx_users_referred_by' not in existing_indexes:
                conn.execute(text("CREATE INDEX idx_users_referred_by ON users (referred_by)"))
            
            conn.commit()
            print("✅ Phase 7 migration completed successfully!")

def downgrade():
    app = create_app()
    with app.app_context():
        with db.engine.connect() as conn:
            # Drop referrals table and related indexes
            conn.execute(text("DROP TABLE IF EXISTS referrals"))
            conn.execute(text("DROP INDEX IF EXISTS idx_referrals_referrer"))
            conn.execute(text("DROP INDEX IF EXISTS idx_referrals_referred"))
            conn.execute(text("DROP INDEX IF EXISTS idx_referrals_code"))
            conn.execute(text("DROP INDEX IF EXISTS idx_users_referral_code"))
            conn.execute(text("DROP INDEX IF EXISTS idx_users_referred_by"))
            
            conn.commit()
            print("✅ Phase 7 migration rolled back successfully!")

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'downgrade':
        downgrade()
    else:
        upgrade() 