#!/usr/bin/env python3
"""
Test script for the chat system
Creates sample data to demonstrate the chat functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, Video, ChatMessage, ChatReaction, ChatReply
from datetime import datetime

def create_test_data():
    """Create test data for the chat system"""
    app = create_app()
    
    with app.app_context():
        print("🗨️ Creating test data for chat system...")
        
        try:
            # Create test users if they don't exist
            user1 = User.query.filter_by(email='user1@test.com').first()
            if not user1:
                user1 = User(email='user1@test.com')
                user1.set_password('password123')
                user1.email_verified = True  # Enable login
                user1.credits = 100
                db.session.add(user1)
            
            user2 = User.query.filter_by(email='user2@test.com').first()
            if not user2:
                user2 = User(email='user2@test.com')
                user2.set_password('password123')
                user2.email_verified = True  # Enable login
                user2.credits = 100
                db.session.add(user2)
            
            db.session.commit()
            
            # Create a test video if it doesn't exist
            video = Video.query.filter_by(prompt='Amazing sunset over the ocean').first()
            if not video:
                video = Video(
                    user_id=user1.id,
                    prompt='Amazing sunset over the ocean with waves crashing',
                    quality='1080p',
                    status='completed',
                    public=True,
                    gcs_signed_url='https://example.com/video.mp4',
                    thumbnail_url='https://example.com/thumb.jpg'
                )
                db.session.add(video)
                db.session.commit()
            
            # Create sample chat messages
            if not ChatMessage.query.filter_by(video_id=video.id).first():
                # Main messages
                msg1 = ChatMessage(
                    video_id=video.id,
                    user_id=user1.id,
                    content="Wow, this is absolutely stunning! The colors in this sunset are incredible."
                )
                db.session.add(msg1)
                
                msg2 = ChatMessage(
                    video_id=video.id,
                    user_id=user2.id,
                    content="I agree! The way the light reflects on the water is so realistic. AI has come so far!"
                )
                db.session.add(msg2)
                
                msg3 = ChatMessage(
                    video_id=video.id,
                    user_id=user1.id,
                    content="The wave animations look so natural too. What prompt did you use for this?"
                )
                db.session.add(msg3)
                
                db.session.commit()
                
                # Add some reactions
                reactions = [
                    ChatReaction(message_id=msg1.id, user_id=user2.id, emoji='❤️'),
                    ChatReaction(message_id=msg1.id, user_id=user1.id, emoji='🔥'),
                    ChatReaction(message_id=msg2.id, user_id=user1.id, emoji='👍'),
                    ChatReaction(message_id=msg3.id, user_id=user2.id, emoji='🤔'),
                ]
                
                for reaction in reactions:
                    db.session.add(reaction)
                
                # Add some replies
                reply1 = ChatReply(
                    message_id=msg2.id,
                    user_id=user1.id,
                    content="Totally! I remember when AI videos looked like glitchy slideshows 😂"
                )
                db.session.add(reply1)
                
                reply2 = ChatReply(
                    message_id=msg2.id,
                    user_id=user2.id,
                    content="Right? The quality improvement just in the last year has been mind-blowing!"
                )
                db.session.add(reply2)
                
                reply3 = ChatReply(
                    message_id=msg3.id,
                    user_id=user2.id,
                    content="I used: 'Cinematic sunset over ocean with golden hour lighting, gentle waves, 4K quality, photorealistic'"
                )
                db.session.add(reply3)
                
                db.session.commit()
                
                # Add reactions to replies
                reply_reactions = [
                    ChatReaction(reply_id=reply1.id, user_id=user2.id, emoji='😂'),
                    ChatReaction(reply_id=reply3.id, user_id=user1.id, emoji='💯'),
                ]
                
                for reaction in reply_reactions:
                    db.session.add(reaction)
                
                db.session.commit()
                
                print("✅ Sample chat data created successfully!")
                print(f"   - Video: {video.prompt}")
                print(f"   - Messages: {ChatMessage.query.filter_by(video_id=video.id).count()}")
                print(f"   - Replies: {ChatReply.query.count()}")
                print(f"   - Reactions: {ChatReaction.query.count()}")
                print(f"   - Users: user1@test.com, user2@test.com (password: password123)")
                
            else:
                print("✅ Test data already exists!")
                
        except Exception as e:
            print(f"❌ Error creating test data: {e}")
            return False
    
    return True

if __name__ == "__main__":
    print("🧪 Setting up chat system test data...")
    success = create_test_data()
    
    if success:
        print("\n🎉 Test data setup completed!")
        print("\n📋 Test Instructions:")
        print("1. Start the Flask app: python run.py")
        print("2. Visit http://localhost:5000")
        print("3. Register or login with test accounts:")
        print("   - user1@test.com / password123")
        print("   - user2@test.com / password123")
        print("4. Look for the chat icon on video cards (index page)")
        print("5. Click on a video to see embedded chat (watch page)")
        print("6. Test features:")
        print("   - Send messages")
        print("   - Add emoji reactions")
        print("   - Reply to messages")
        print("   - View threaded conversations")
    else:
        print("\n💥 Test data setup failed.")
        sys.exit(1)