#!/usr/bin/env python3
"""
Migration script to add chat tables to the database
Run this script to create the new chat-related tables
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import ChatMessage, ChatReaction, ChatReply

def add_chat_tables():
    """Add chat tables to the database"""
    app = create_app()
    
    with app.app_context():
        print("Creating chat tables...")
        
        try:
            # Create the new tables
            db.create_all()
            print("✅ Chat tables created successfully!")
            
            # Verify tables were created
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            expected_tables = ['chat_messages', 'chat_reactions', 'chat_replies']
            for table in expected_tables:
                if table in tables:
                    print(f"✅ Table '{table}' created")
                else:
                    print(f"❌ Table '{table}' NOT found")
                    
        except Exception as e:
            print(f"❌ Error creating chat tables: {e}")
            return False
    
    return True

if __name__ == "__main__":
    print("🗨️ Adding chat system tables to database...")
    success = add_chat_tables()
    
    if success:
        print("\n🎉 Chat system database migration completed successfully!")
        print("You can now run the application and use the chat features.")
    else:
        print("\n💥 Migration failed. Please check the error messages above.")
        sys.exit(1)