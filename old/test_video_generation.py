#!/usr/bin/env python3
"""
Test video generation in mock mode
"""

from app import create_app, db
from app.models import User, Video
from app.tasks import generate_video_task
from datetime import datetime

def test_video_generation():
    """Test video generation in mock mode"""
    app = create_app()
    
    with app.app_context():
        # Get the first user
        user = User.query.first()
        if not user:
            print("❌ No users found in database")
            return
        
        print(f"👤 Testing with user: {user.email}")
        print(f"💰 Credits: {user.credits}")
        print(f"📊 API calls today: {user.api_calls_today}")
        
        # Create a test video
        video = Video(
            user_id=user.id,
            prompt="A beautiful sunset over the ocean",
            quality="360p"
        )
        
        db.session.add(video)
        db.session.commit()
        
        print(f"🎬 Created video - ID: {video.id}, Status: {video.status}")
        print(f"🔗 Slug: {video.slug}")
        
        # Generate the video
        try:
            print("🚀 Starting video generation...")
            result = generate_video_task(video.id)
            print(f"✅ Video generation result: {result}")
            
            # Check the video status
            video = Video.query.get(video.id)
            print(f"📊 Final video status: {video.status}")
            print(f"🔗 Final slug: {video.slug}")
            print(f"🎥 Video URL: {video.gcs_signed_url}")
            
        except Exception as e:
            print(f"❌ Error generating video: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_video_generation() 