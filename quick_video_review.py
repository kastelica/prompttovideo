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

def quick_video_review():
    """Quick review of videos - mark as good/bad and collect issues"""
    print("🔍 QUICK VIDEO REVIEW - CLOUD SQL")
    print("=" * 50)
    
    app = create_app()
    with app.app_context():
        # Get all videos
        videos = Video.query.order_by(Video.created_at.desc()).all()
        
        if not videos:
            print("❌ No videos found in database")
            return
        
        print(f"✅ Found {len(videos)} videos to review")
        print()
        
        # Track results
        good_videos = []
        bad_videos = []
        issues = {
            'wrong_url': [],
            'wrong_thumbnail': [],
            'wrong_title': [],
            'wrong_slug': [],
            'missing_file': [],
            'other': []
        }
        
        # Review each video
        for i, video in enumerate(videos):
            print(f"🎬 Video {i+1}/{len(videos)} (ID: {video.id})")
            print(f"   Title: {video.title or 'N/A'}")
            print(f"   Prompt: {video.prompt[:60]}...")
            print(f"   Status: {video.status}")
            print(f"   Slug: {video.slug or 'N/A'}")
            print(f"   GCS URL: {video.gcs_url or 'N/A'}")
            print(f"   Thumbnail: {video.thumbnail_url or 'N/A'}")
            print()
            
            while True:
                response = input("Is this video GOOD? (y/n/q to quit): ").lower().strip()
                
                if response == 'q':
                    print("👋 Quitting review...")
                    break
                elif response == 'y':
                    good_videos.append(video.id)
                    print(f"✅ Marked video {video.id} as GOOD")
                    break
                elif response == 'n':
                    bad_videos.append(video.id)
                    print("What's wrong with this video?")
                    print("1. Wrong video URL")
                    print("2. Wrong thumbnail")
                    print("3. Wrong title")
                    print("4. Wrong slug")
                    print("5. Missing file")
                    print("6. Other issue")
                    
                    issue_choice = input("Select issue (1-6): ").strip()
                    
                    if issue_choice == '1':
                        issues['wrong_url'].append(video.id)
                    elif issue_choice == '2':
                        issues['wrong_thumbnail'].append(video.id)
                    elif issue_choice == '3':
                        issues['wrong_title'].append(video.id)
                    elif issue_choice == '4':
                        issues['wrong_slug'].append(video.id)
                    elif issue_choice == '5':
                        issues['missing_file'].append(video.id)
                    elif issue_choice == '6':
                        issues['other'].append(video.id)
                    
                    print(f"❌ Marked video {video.id} as BAD")
                    break
                else:
                    print("Please enter 'y', 'n', or 'q'")
            
            if response == 'q':
                break
            
            print("-" * 50)
        
        # Print summary
        print("\n📊 REVIEW SUMMARY")
        print("=" * 50)
        print(f"Total videos reviewed: {len(good_videos) + len(bad_videos)}")
        print(f"Good videos: {len(good_videos)}")
        print(f"Bad videos: {len(bad_videos)}")
        
        if bad_videos:
            print("\n🚨 ISSUES FOUND:")
            for issue_type, video_ids in issues.items():
                if video_ids:
                    print(f"   {issue_type}: {len(video_ids)} videos")
                    print(f"      Video IDs: {video_ids}")
        
        # Offer bulk fix options
        if bad_videos:
            print("\n🔧 BULK FIX OPTIONS:")
            print("=" * 50)
            
            if issues['wrong_url']:
                print("1. Fix wrong video URLs")
            if issues['wrong_thumbnail']:
                print("2. Fix wrong thumbnails")
            if issues['wrong_title']:
                print("3. Fix wrong titles")
            if issues['wrong_slug']:
                print("4. Fix wrong slugs")
            if issues['missing_file']:
                print("5. Handle missing files")
            
            print("6. Delete videos from database")
            print("7. Export issues to file")
            print("8. Exit without fixing")
            
            choice = input("\nSelect option (1-8): ").strip()
            
            if choice == '1' and issues['wrong_url']:
                fix_wrong_urls(issues['wrong_url'])
            elif choice == '2' and issues['wrong_thumbnail']:
                fix_wrong_thumbnails(issues['wrong_thumbnail'])
            elif choice == '3' and issues['wrong_title']:
                fix_wrong_titles(issues['wrong_title'])
            elif choice == '4' and issues['wrong_slug']:
                fix_wrong_slugs(issues['wrong_slug'])
            elif choice == '5' and issues['missing_file']:
                handle_missing_files(issues['missing_file'])
            elif choice == '6':
                delete_videos_from_db(bad_videos)
            elif choice == '7':
                export_issues(issues, good_videos, bad_videos)
            else:
                print("👋 Exiting without fixes")
        else:
            print("✅ All videos are good!")

def fix_wrong_urls(video_ids):
    """Fix wrong video URLs"""
    print(f"🔧 FIXING WRONG URLS FOR {len(video_ids)} VIDEOS")
    print("=" * 50)
    
    app = create_app()
    with app.app_context():
        for video_id in video_ids:
            video = Video.query.get(video_id)
            if video:
                print(f"\n🎬 Video {video_id}: {video.title or video.prompt[:50]}")
                print(f"   Current URL: {video.gcs_url}")
                new_url = input(f"   Enter correct GCS URL (or press Enter to skip): ").strip()
                
                if new_url:
                    try:
                        video.gcs_url = new_url
                        video.updated_at = datetime.now(timezone.utc)
                        db.session.commit()
                        print(f"   ✅ Updated URL")
                    except Exception as e:
                        print(f"   ❌ Error: {str(e)}")
                        db.session.rollback()

def fix_wrong_thumbnails(video_ids):
    """Fix wrong thumbnails"""
    print(f"🔧 FIXING WRONG THUMBNAILS FOR {len(video_ids)} VIDEOS")
    print("=" * 50)
    
    app = create_app()
    with app.app_context():
        for video_id in video_ids:
            video = Video.query.get(video_id)
            if video:
                print(f"\n🎬 Video {video_id}: {video.title or video.prompt[:50]}")
                print(f"   Current thumbnail: {video.thumbnail_url}")
                new_thumb = input(f"   Enter correct thumbnail URL (or press Enter to skip): ").strip()
                
                if new_thumb:
                    try:
                        video.thumbnail_url = new_thumb
                        video.updated_at = datetime.now(timezone.utc)
                        db.session.commit()
                        print(f"   ✅ Updated thumbnail")
                    except Exception as e:
                        print(f"   ❌ Error: {str(e)}")
                        db.session.rollback()

def fix_wrong_titles(video_ids):
    """Fix wrong titles"""
    print(f"🔧 FIXING WRONG TITLES FOR {len(video_ids)} VIDEOS")
    print("=" * 50)
    
    app = create_app()
    with app.app_context():
        for video_id in video_ids:
            video = Video.query.get(video_id)
            if video:
                print(f"\n🎬 Video {video_id}")
                print(f"   Current title: {video.title or 'N/A'}")
                print(f"   Prompt: {video.prompt[:50]}...")
                new_title = input(f"   Enter correct title (or press Enter to skip): ").strip()
                
                if new_title:
                    try:
                        video.title = new_title
                        video.updated_at = datetime.now(timezone.utc)
                        db.session.commit()
                        print(f"   ✅ Updated title")
                    except Exception as e:
                        print(f"   ❌ Error: {str(e)}")
                        db.session.rollback()

def fix_wrong_slugs(video_ids):
    """Fix wrong slugs"""
    print(f"🔧 FIXING WRONG SLUGS FOR {len(video_ids)} VIDEOS")
    print("=" * 50)
    
    app = create_app()
    with app.app_context():
        for video_id in video_ids:
            video = Video.query.get(video_id)
            if video:
                print(f"\n🎬 Video {video_id}: {video.title or video.prompt[:50]}")
                print(f"   Current slug: {video.slug or 'N/A'}")
                new_slug = input(f"   Enter correct slug (or press Enter to skip): ").strip()
                
                if new_slug:
                    try:
                        video.slug = new_slug
                        video.updated_at = datetime.now(timezone.utc)
                        db.session.commit()
                        print(f"   ✅ Updated slug")
                    except Exception as e:
                        print(f"   ❌ Error: {str(e)}")
                        db.session.rollback()

def handle_missing_files(video_ids):
    """Handle missing files"""
    print(f"🔧 HANDLING MISSING FILES FOR {len(video_ids)} VIDEOS")
    print("=" * 50)
    print("Options:")
    print("1. Mark videos as failed")
    print("2. Skip for now")
    
    choice = input("Select option (1-2): ").strip()
    
    app = create_app()
    with app.app_context():
        if choice == '1':
            for video_id in video_ids:
                video = Video.query.get(video_id)
                if video:
                    video.status = 'failed'
                    video.updated_at = datetime.now(timezone.utc)
                    db.session.commit()
                    print(f"✅ Marked video {video_id} as failed")

def delete_videos_from_db(video_ids):
    """Delete videos from database"""
    print(f"🗑️ DELETE VIDEOS FROM DATABASE")
    print("=" * 50)
    print(f"⚠️ WARNING: This will permanently delete {len(video_ids)} videos from the database!")
    print("This action cannot be undone.")
    print()
    print("Video IDs to delete:", video_ids)
    print()
    
    # Show video details before deletion
    app = create_app()
    with app.app_context():
        print("📋 VIDEOS TO BE DELETED:")
        for video_id in video_ids:
            video = Video.query.get(video_id)
            if video:
                print(f"   ID {video_id}: {video.title or video.prompt[:50]}...")
            else:
                print(f"   ID {video_id}: Not found in database")
        print()
    
    confirm = input("Are you ABSOLUTELY sure you want to delete these videos? (type 'DELETE' to confirm): ").strip()
    
    if confirm == 'DELETE':
        app = create_app()
        with app.app_context():
            deleted_count = 0
            errors = []
            
            for video_id in video_ids:
                try:
                    video = Video.query.get(video_id)
                    if video:
                        # Delete related records first to avoid foreign key constraints
                        from app.models import ChatMessage, ChallengeSubmission
                        
                        # Delete chat messages
                        ChatMessage.query.filter_by(video_id=video_id).delete()
                        
                        # Delete challenge submissions
                        ChallengeSubmission.query.filter_by(video_id=video_id).delete()
                        
                        # Delete the video
                        db.session.delete(video)
                        db.session.commit()
                        deleted_count += 1
                        print(f"✅ Deleted video {video_id}")
                    else:
                        print(f"⚠️ Video {video_id} not found in database")
                        errors.append(f"Video {video_id} not found")
                except Exception as e:
                    print(f"❌ Error deleting video {video_id}: {str(e)}")
                    db.session.rollback()
                    errors.append(f"Video {video_id}: {str(e)}")
            
            print(f"\n📊 DELETION SUMMARY:")
            print(f"   Successfully deleted: {deleted_count}")
            print(f"   Errors: {len(errors)}")
            
            if errors:
                print("\n❌ ERRORS:")
                for error in errors:
                    print(f"   - {error}")
    else:
        print("❌ Deletion cancelled")

def export_issues(issues, good_videos, bad_videos):
    """Export issues to a file"""
    filename = f"video_issues_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    with open(filename, 'w') as f:
        f.write("VIDEO REVIEW RESULTS\n")
        f.write("=" * 50 + "\n")
        f.write(f"Total videos: {len(good_videos) + len(bad_videos)}\n")
        f.write(f"Good videos: {len(good_videos)}\n")
        f.write(f"Bad videos: {len(bad_videos)}\n\n")
        
        f.write("GOOD VIDEOS:\n")
        f.write(f"Video IDs: {good_videos}\n\n")
        
        f.write("BAD VIDEOS:\n")
        for issue_type, video_ids in issues.items():
            if video_ids:
                f.write(f"{issue_type}: {video_ids}\n")
    
    print(f"✅ Issues exported to {filename}")

def main():
    print("🔍 QUICK VIDEO REVIEW TOOL")
    print("=" * 50)
    
    try:
        quick_video_review()
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main() 