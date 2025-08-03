#!/usr/bin/env python3
"""
Troubleshoot video mappings between database, GCS, thumbnails, and watch pages.
"""

import os
import sys
from sqlalchemy import and_, or_, text

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Set production environment variables for Cloud SQL
os.environ['FLASK_ENV'] = 'production'
os.environ['FLASK_DEBUG'] = '0'

# Set the Cloud SQL database URL
CLOUD_SQL_URL = "postgresql://prompttovideo:PromptToVideo2024!@34.46.33.136:5432/prompttovideo"
os.environ['DATABASE_URL'] = CLOUD_SQL_URL

print(f"🔗 Connecting to Cloud SQL database...")
print(f"   URL: {CLOUD_SQL_URL}")

from app import create_app, db
from app.models import Video, User
from app.gcs_utils import get_file_info_from_gcs, generate_signed_url, generate_signed_thumbnail_url

def check_video_mappings():
    """Check all video mappings and identify issues."""
    app = create_app()
    
    with app.app_context():
        print("🔍 TROUBLESHOOTING VIDEO MAPPINGS")
        print("=" * 50)
        
        # Get all videos
        all_videos = Video.query.order_by(Video.id).all()
        print(f"📊 Total videos in database: {len(all_videos)}")
        
        issues = []
        working_videos = []
        
        for video in all_videos:
            print(f"\n🎬 Video ID {video.id}: {video.prompt[:50]}...")
            print(f"   Status: {video.status}")
            print(f"   Views: {video.views}")
            print(f"   Created: {video.created_at}")
            print(f"   User: {video.user.email if video.user else 'Unknown'}")
            
            video_issues = []
            
            # Check GCS video URL
            if video.gcs_url:
                print(f"   🗂️  GCS Video: {video.gcs_url}")
                file_info = get_file_info_from_gcs(video.gcs_url)
                if file_info.get('exists'):
                    print(f"      ✅ GCS video exists")
                else:
                    print(f"      ❌ GCS video NOT FOUND")
                    video_issues.append("GCS video missing")
            else:
                print(f"   🗂️  GCS Video: None")
                video_issues.append("No GCS URL")
            
            # Check thumbnail
            print(f"   🖼️  Thumbnail GCS: {video.thumbnail_gcs_url}")
            if video.thumbnail_gcs_url:
                file_info = get_file_info_from_gcs(video.thumbnail_gcs_url)
                if file_info.get('exists'):
                    print(f"      ✅ GCS thumbnail exists")
                else:
                    print(f"      ❌ GCS thumbnail NOT FOUND")
                    video_issues.append("GCS thumbnail missing")
            else:
                print(f"      ⚠️  No GCS thumbnail URL")
                video_issues.append("No GCS thumbnail URL")
            
            # Check thumbnail_url field
            print(f"   🖼️  Thumbnail URL: {video.thumbnail_url}")
            
            # Test get_thumbnail_url() method
            try:
                thumbnail_url = video.get_thumbnail_url()
                print(f"   🖼️  get_thumbnail_url(): {thumbnail_url}")
                if thumbnail_url:
                    print(f"      ✅ Thumbnail URL generated")
                else:
                    print(f"      ❌ No thumbnail URL generated")
                    video_issues.append("get_thumbnail_url() returns None")
            except Exception as e:
                print(f"      ❌ Error in get_thumbnail_url(): {e}")
                video_issues.append(f"get_thumbnail_url() error: {e}")
            
            # Check watch page URL
            try:
                watch_url = f"/watch/{video.id}"
                print(f"   📺 Watch URL: {watch_url}")
                print(f"      ✅ Watch URL generated")
            except Exception as e:
                print(f"      ❌ Error generating watch URL: {e}")
                video_issues.append(f"Watch URL error: {e}")
            
            # Check if video is accessible
            if video.status == 'completed' and video.gcs_url:
                try:
                    signed_url = generate_signed_url(video.gcs_url, duration_days=1)
                    print(f"   🔗 Signed Video URL: {signed_url[:80]}...")
                    print(f"      ✅ Signed URL generated")
                except Exception as e:
                    print(f"      ❌ Error generating signed URL: {e}")
                    video_issues.append(f"Signed URL error: {e}")
            
            # Summary for this video
            if video_issues:
                print(f"   ❌ ISSUES: {', '.join(video_issues)}")
                issues.append({
                    'video_id': video.id,
                    'prompt': video.prompt,
                    'status': video.status,
                    'issues': video_issues
                })
            else:
                print(f"   ✅ All mappings working correctly")
                working_videos.append(video.id)
        
        # Summary
        print(f"\n📊 MAPPING SUMMARY:")
        print(f"   Total videos: {len(all_videos)}")
        print(f"   Working videos: {len(working_videos)}")
        print(f"   Videos with issues: {len(issues)}")
        
        if issues:
            print(f"\n❌ VIDEOS WITH ISSUES:")
            for issue in issues:
                print(f"   ID {issue['video_id']}: {issue['prompt'][:40]}...")
                print(f"      Status: {issue['status']}")
                print(f"      Issues: {', '.join(issue['issues'])}")
                print()
        
        if working_videos:
            print(f"\n✅ WORKING VIDEOS:")
            print(f"   IDs: {', '.join(map(str, working_videos))}")
        
        return {
            'total': len(all_videos),
            'working': len(working_videos),
            'issues': len(issues),
            'issue_details': issues
        }

def check_specific_video(video_id):
    """Check a specific video's mappings in detail."""
    app = create_app()
    
    with app.app_context():
        video = Video.query.get(video_id)
        if not video:
            print(f"❌ Video ID {video_id} not found")
            return
        
        print(f"🔍 DETAILED CHECK FOR VIDEO ID {video_id}")
        print("=" * 50)
        print(f"Prompt: {video.prompt}")
        print(f"Status: {video.status}")
        print(f"Views: {video.views}")
        print(f"Created: {video.created_at}")
        print(f"User: {video.user.email if video.user else 'Unknown'}")
        
        # Database fields
        print(f"\n📊 DATABASE FIELDS:")
        print(f"   gcs_url: {video.gcs_url}")
        print(f"   thumbnail_gcs_url: {video.thumbnail_gcs_url}")
        print(f"   thumbnail_url: {video.thumbnail_url}")
        print(f"   slug: {getattr(video, 'slug', 'No slug field')}")
        
        # GCS checks
        print(f"\n🗂️  GCS CHECKS:")
        if video.gcs_url:
            file_info = get_file_info_from_gcs(video.gcs_url)
            exists = file_info.get('exists')
            print(f"   Video file exists: {exists}")
            if exists:
                try:
                    signed_url = generate_signed_url(video.gcs_url, duration_days=1)
                    print(f"   Signed URL: {signed_url}")
                except Exception as e:
                    print(f"   Signed URL error: {e}")
        else:
            print(f"   No GCS URL")
        
        if video.thumbnail_gcs_url:
            file_info = get_file_info_from_gcs(video.thumbnail_gcs_url)
            exists = file_info.get('exists')
            print(f"   Thumbnail file exists: {exists}")
            if exists:
                try:
                    signed_thumb_url = generate_signed_url(video.thumbnail_gcs_url, duration_days=1)
                    print(f"   Signed thumbnail URL: {signed_thumb_url}")
                except Exception as e:
                    print(f"   Signed thumbnail URL error: {e}")
        else:
            print(f"   No GCS thumbnail URL")
        
        # URL generation tests
        print(f"\n🔗 URL GENERATION TESTS:")
        try:
            thumbnail_url = video.get_thumbnail_url()
            print(f"   get_thumbnail_url(): {thumbnail_url}")
        except Exception as e:
            print(f"   get_thumbnail_url() error: {e}")
        
        try:
            watch_url = f"/watch/{video.id}"
            print(f"   Watch URL: {watch_url}")
        except Exception as e:
            print(f"   Watch URL error: {e}")
        
        # Test thumbnail generation if missing
        if not video.get_thumbnail_url() and video.gcs_url:
            print(f"\n🔄 ATTEMPTING THUMBNAIL GENERATION:")
            try:
                from app.video_processor import generate_thumbnail
                thumbnail_gcs_url = generate_thumbnail(video.gcs_url, video.id)
                print(f"   Generated thumbnail: {thumbnail_gcs_url}")
                
                # Update database
                video.thumbnail_gcs_url = thumbnail_gcs_url
                db.session.commit()
                print(f"   ✅ Database updated")
                
                # Test new thumbnail URL
                new_thumbnail_url = video.get_thumbnail_url()
                print(f"   New get_thumbnail_url(): {new_thumbnail_url}")
                
            except Exception as e:
                print(f"   ❌ Thumbnail generation failed: {e}")

def fix_video_mappings():
    """Attempt to fix common video mapping issues."""
    app = create_app()
    
    with app.app_context():
        print("🔧 FIXING VIDEO MAPPINGS")
        print("=" * 40)
        
        # Find videos with missing thumbnails
        videos_without_thumbnails = []
        all_videos = Video.query.all()
        
        for video in all_videos:
            if not video.get_thumbnail_url() and video.gcs_url and video.status == 'completed':
                videos_without_thumbnails.append(video)
        
        print(f"Found {len(videos_without_thumbnails)} completed videos without thumbnails")
        
        if not videos_without_thumbnails:
            print("✅ No videos need thumbnail generation")
            return
        
        fixed_count = 0
        errors = []
        
        for video in videos_without_thumbnails:
            print(f"\n🎬 Fixing Video ID {video.id}: {video.prompt[:40]}...")
            
            try:
                from app.video_processor import generate_thumbnail
                
                # Generate thumbnail
                thumbnail_gcs_url = generate_thumbnail(video.gcs_url, video.id)
                print(f"   Generated: {thumbnail_gcs_url}")
                
                # Update database
                video.thumbnail_gcs_url = thumbnail_gcs_url
                db.session.commit()
                print(f"   ✅ Database updated")
                
                # Verify
                new_thumbnail_url = video.get_thumbnail_url()
                if new_thumbnail_url:
                    print(f"   ✅ Thumbnail URL working: {new_thumbnail_url}")
                    fixed_count += 1
                else:
                    print(f"   ❌ Thumbnail URL still not working")
                    errors.append(f"Video {video.id}: Thumbnail URL not working after generation")
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
                errors.append(f"Video {video.id}: {e}")
                db.session.rollback()
        
        print(f"\n📊 FIX SUMMARY:")
        print(f"   Videos processed: {len(videos_without_thumbnails)}")
        print(f"   Successfully fixed: {fixed_count}")
        print(f"   Errors: {len(errors)}")
        
        if errors:
            print(f"\n❌ ERRORS:")
            for error in errors:
                print(f"   {error}")

def main():
    """Main menu for video mapping troubleshooting."""
    while True:
        print("\n🔍 VIDEO MAPPING TROUBLESHOOTER")
        print("=" * 40)
        print("1. Check all video mappings")
        print("2. Check specific video")
        print("3. Fix missing thumbnails")
        print("4. Exit")
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == '1':
            check_video_mappings()
        elif choice == '2':
            try:
                video_id = int(input("Enter video ID: ").strip())
                check_specific_video(video_id)
            except ValueError:
                print("❌ Invalid video ID")
        elif choice == '3':
            fix_video_mappings()
        elif choice == '4':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid option")

if __name__ == "__main__":
    main() 