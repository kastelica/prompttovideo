#!/usr/bin/env python3
"""
Check Frontend Videos Script

This script shows what videos are being displayed on index and dashboard pages
by replicating the same database queries used in the routes.
"""

import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app, db
from app.models import Video, User
from sqlalchemy import and_, or_

def check_frontend_videos():
    """Check what videos are being displayed on frontend pages"""
    print("🔍 ===== CHECKING FRONTEND VIDEOS =====")
    print()
    
    app = create_app()
    with app.app_context():
        # Get all videos first
        all_videos = Video.query.all()
        print(f"📊 Total videos in database: {len(all_videos)}")
        print()
        
        # ===== INDEX PAGE QUERY (from app/main/routes.py) =====
        print("🏠 ===== INDEX PAGE VIDEOS =====")
        print("Query: Video.public == True AND Video.status == 'completed' AND Video.gcs_signed_url.isnot(None)")
        print()
        
        featured_videos = Video.query.filter(
            and_(
                Video.public == True,
                Video.status == 'completed',
                Video.gcs_signed_url.isnot(None)
            )
        ).limit(12).all()
        
        print(f"📺 Featured videos on index: {len(featured_videos)}")
        if featured_videos:
            for video in featured_videos:
                print(f"   - ID: {video.id}, Title: '{video.title}', Status: {video.status}")
                print(f"     Public: {video.public}, GCS URL: {bool(video.gcs_url)}, Signed URL: {bool(video.gcs_signed_url)}")
                print(f"     Created: {video.created_at}")
                print()
        else:
            print("   ❌ No videos displayed on index page")
        print()
        
        # ===== DASHBOARD PAGE QUERY (from app/main/routes.py) =====
        print("📊 ===== DASHBOARD PAGE VIDEOS =====")
        print("Query: Video.user_id == user_id AND Video.status.in_(['completed', 'processing', 'pending'])")
        print("Note: Dashboard shows videos by status, regardless of GCS URLs")
        print()
        
        # Check for a sample user (first user in database)
        sample_user = User.query.first()
        if sample_user:
            print(f"👤 Checking dashboard for user: {sample_user.email} (ID: {sample_user.id})")
            
            dashboard_videos = Video.query.filter(
                and_(
                    Video.user_id == sample_user.id,
                    Video.status.in_(['completed', 'processing', 'pending'])
                )
            ).order_by(Video.created_at.desc()).all()
            
            print(f"📺 Dashboard videos for user: {len(dashboard_videos)}")
            if dashboard_videos:
                for video in dashboard_videos:
                    print(f"   - ID: {video.id}, Title: '{video.title}', Status: {video.status}")
                    print(f"     GCS URL: {bool(video.gcs_url)}, Signed URL: {bool(video.gcs_signed_url)}")
                    print(f"     Created: {video.created_at}")
                    print()
            else:
                print("   ❌ No videos displayed on dashboard")
        else:
            print("   ❌ No users found in database")
        print()
        
        # ===== PROFILE PAGE QUERY (via API) =====
        print("👤 ===== PROFILE PAGE VIDEOS =====")
        print("Query: Video.user_id == user_id AND Video.status.in_(['completed', 'processing', 'pending'])")
        print("Note: Profile page uses same query as dashboard")
        print()
        
        if sample_user:
            profile_videos = Video.query.filter(
                and_(
                    Video.user_id == sample_user.id,
                    Video.status.in_(['completed', 'processing', 'pending'])
                )
            ).order_by(Video.created_at.desc()).all()
            
            print(f"📺 Profile videos for user: {len(profile_videos)}")
            if profile_videos:
                for video in profile_videos:
                    print(f"   - ID: {video.id}, Title: '{video.title}', Status: {video.status}")
                    print(f"     GCS URL: {bool(video.gcs_url)}, Signed URL: {bool(video.gcs_signed_url)}")
                    print(f"     Created: {video.created_at}")
                    print()
            else:
                print("   ❌ No videos displayed on profile")
        print()
        
        # ===== SUMMARY =====
        print("📋 ===== SUMMARY =====")
        print(f"Total videos in database: {len(all_videos)}")
        print(f"Videos with GCS URLs: {len([v for v in all_videos if v.gcs_url])}")
        print(f"Videos with signed URLs: {len([v for v in all_videos if v.gcs_signed_url])}")
        print(f"Public videos: {len([v for v in all_videos if v.public])}")
        print(f"Completed videos: {len([v for v in all_videos if v.status == 'completed'])}")
        print(f"Processing videos: {len([v for v in all_videos if v.status == 'processing'])}")
        print(f"Pending videos: {len([v for v in all_videos if v.status == 'pending'])}")
        print()
        
        print("🎯 ===== WHY VIDEOS APPEAR/DON'T APPEAR =====")
        print()
        
        # Check why videos don't appear on index
        completed_public_videos = Video.query.filter(
            and_(
                Video.public == True,
                Video.status == 'completed'
            )
        ).all()
        
        print(f"✅ Videos that SHOULD appear on index (public + completed): {len(completed_public_videos)}")
        for video in completed_public_videos:
            if not video.gcs_signed_url:
                print(f"   ❌ Video {video.id} missing signed URL (won't show on index)")
        
        # Check dashboard videos
        if sample_user:
            dashboard_eligible = Video.query.filter(
                and_(
                    Video.user_id == sample_user.id,
                    Video.status.in_(['completed', 'processing', 'pending'])
                )
            ).all()
            
            print(f"✅ Videos that SHOULD appear on dashboard: {len(dashboard_eligible)}")
            for video in dashboard_eligible:
                if not video.gcs_url and not video.gcs_signed_url:
                    print(f"   ⚠️ Video {video.id} has no GCS URLs (will show but can't play)")

if __name__ == "__main__":
    check_frontend_videos() 