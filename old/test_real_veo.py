#!/usr/bin/env python3
"""
Test real Veo API video generation
"""

from app import create_app, db
from app.models import User, Video
from app.tasks import generate_video_task
from datetime import datetime

def test_real_veo():
    """Test real Veo API video generation"""
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
        print("🔐 Using REAL Veo API (not mock mode)")
        print()
        
        # Create a test video
        video = Video(
            user_id=user.id,
            prompt="A beautiful sunset over the ocean with waves crashing on the shore",
            quality="360p"
        )
        
        db.session.add(video)
        db.session.commit()
        
        print(f"🎬 Created video - ID: {video.id}, Status: {video.status}")
        print(f"🔗 Slug: {video.slug}")
        print()
        print("🚀 Starting REAL video generation (this may take 1-5 minutes)...")
        print("⚠️  This will make actual API calls and may incur charges!")
        print()
        
        # Generate the video
        try:
            result = generate_video_task(video.id)
            print(f"✅ Video generation result: {result}")
            
            # Check the video status
            video = Video.query.get(video.id)
            print(f"📊 Final video status: {video.status}")
            print(f"🔗 Final slug: {video.slug}")
            print(f"🎥 Video URL: {video.gcs_signed_url}")
            
            if video.status == 'completed':
                print("🎉 SUCCESS! Real video was generated!")
                print("🔗 You can watch it at the URL above")
            else:
                print(f"❌ Video generation failed or is still processing: {video.status}")
            
        except Exception as e:
            print(f"❌ Error generating video: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_real_veo() 