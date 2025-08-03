import os
import sys
from datetime import datetime, timezone

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app, db
from app.models import Video, User

# Force production environment
os.environ['FLASK_ENV'] = 'production'
os.environ['FLASK_DEBUG'] = '0'

# Set Cloud SQL connection string
os.environ['DATABASE_URL'] = 'postgresql://prompttovideo:PromptToVideo2024!@34.46.33.136:5432/prompttovideo'

def fix_thumbnail_urls():
    """Fix thumbnail URLs by converting storage.cloud.google.com to storage.googleapis.com"""
    print("🔧 FIXING THUMBNAIL URLS - CLOUD SQL")
    print("=" * 50)
    
    app = create_app()
    with app.app_context():
        # Find videos with problematic thumbnail URLs
        videos_with_bad_urls = Video.query.filter(
            Video.thumbnail_url.like('%storage.cloud.google.com%')
        ).all()
        
        if not videos_with_bad_urls:
            print("✅ No videos found with problematic thumbnail URLs")
            return
        
        print(f"📋 Found {len(videos_with_bad_urls)} videos with problematic thumbnail URLs")
        print()
        
        updated_count = 0
        errors = []
        
        for video in videos_with_bad_urls:
            print(f"🎬 Processing Video ID {video.id}: {video.title or video.prompt[:50]}...")
            print(f"   Current thumbnail_url: {video.thumbnail_url}")
            
            if video.thumbnail_url and 'storage.cloud.google.com' in video.thumbnail_url:
                # Convert storage.cloud.google.com to storage.googleapis.com
                new_url = video.thumbnail_url.replace('storage.cloud.google.com', 'storage.googleapis.com')
                
                print(f"   New thumbnail_url: {new_url}")
                
                try:
                    video.thumbnail_url = new_url
                    video.updated_at = datetime.now(timezone.utc)
                    db.session.commit()
                    
                    print(f"   ✅ Successfully updated thumbnail URL")
                    updated_count += 1
                    
                except Exception as e:
                    print(f"   ❌ Error updating database: {str(e)}")
                    db.session.rollback()
                    errors.append({
                        'video_id': video.id,
                        'error': str(e)
                    })
            else:
                print(f"   ⚠️ No problematic URL found")
            
            print()
        
        print("📊 UPDATE SUMMARY")
        print("=" * 50)
        print(f"Successfully updated: {updated_count}")
        print(f"Errors: {len(errors)}")
        
        if errors:
            print("\n❌ ERRORS:")
            for error in errors:
                print(f"   - Video ID {error['video_id']}: {error['error']}")
        
        if updated_count > 0:
            print(f"\n✅ Successfully fixed {updated_count} thumbnail URLs!")
            print("🎯 Next steps:")
            print("   • Refresh your browser to see the updated thumbnails")
            print("   • Check that thumbnails are now displaying correctly")
        else:
            print("\n⚠️ No thumbnail URLs were updated.")

def main():
    print("🔧 FIX THUMBNAIL URLS - CLOUD SQL")
    print("=" * 50)
    
    try:
        fix_thumbnail_urls()
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main() 