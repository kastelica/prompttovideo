#!/usr/bin/env python3
"""
Archive Existing Files Script

This script moves all existing GCS files to an archive folder and cleans up
the database to only show fresh, newly generated videos from this point forward.
"""

import os
import sys
from datetime import datetime, timezone

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app, db
from app.models import Video
from app.gcs_utils import list_gcs_files, get_gcs_bucket_name
from google.cloud import storage

def get_gcs_client():
    """Get GCS client with proper credentials"""
    creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if not creds_path:
        creds_path = os.path.join(os.getcwd(), 'veo.json')
    
    if os.path.exists(creds_path):
        from google.oauth2 import service_account
        credentials = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        return storage.Client(credentials=credentials)
    else:
        return storage.Client()

def move_file_to_archive(storage_client, bucket_name, old_path, archive_timestamp):
    """Move a file to archive folder"""
    try:
        bucket = storage_client.bucket(bucket_name)
        
        # Create archive path
        archive_path = f"archive/{archive_timestamp}/{old_path}"
        
        # Get source blob
        source_blob = bucket.blob(old_path)
        
        if not source_blob.exists():
            print(f"⚠️ Source file not found: {old_path}")
            return False
        
        # Copy to archive location
        archive_blob = bucket.blob(archive_path)
        bucket.copy_blob(source_blob, bucket, archive_blob.name)
        
        # Delete original file
        source_blob.delete()
        
        print(f"✅ Archived: {old_path} -> {archive_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error archiving {old_path}: {e}")
        return False

def archive_all_existing_files():
    """Move all existing files to archive folder"""
    print("📦 ===== ARCHIVING EXISTING FILES =====")
    print(f"📅 Archive Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print()
    
    # Get archive timestamp
    archive_timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    
    # Get all files in bucket
    files = list_gcs_files()
    
    if not files:
        print("✅ No files to archive")
        return
    
    print(f"📁 Found {len(files)} files to archive")
    print(f"📦 Archive folder: archive/{archive_timestamp}/")
    print()
    
    # Get GCS client
    storage_client = get_gcs_client()
    bucket_name = get_gcs_bucket_name()
    
    # Archive files
    archived_count = 0
    error_count = 0
    
    for file_info in files:
        old_path = file_info['parsed_info']['full_path']
        
        # Skip if already in archive
        if old_path.startswith('archive/'):
            print(f"⏭️ Skipping already archived file: {old_path}")
            continue
        
        success = move_file_to_archive(storage_client, bucket_name, old_path, archive_timestamp)
        if success:
            archived_count += 1
        else:
            error_count += 1
    
    print(f"\n📊 Archive Summary:")
    print(f"   ✅ Archived: {archived_count}")
    print(f"   ❌ Errors: {error_count}")
    print(f"   📁 Total processed: {len(files)}")
    print(f"   📦 Archive location: gs://{bucket_name}/archive/{archive_timestamp}/")
    
    return archive_timestamp

def clean_database_records():
    """Clean up database to only show fresh videos"""
    print("\n🧹 ===== CLEANING DATABASE RECORDS =====")
    print()
    
    app = create_app()
    with app.app_context():
        # Get all videos
        videos = Video.query.all()
        
        print(f"📊 Found {len(videos)} videos in database")
        print()
        
        # Show current status
        status_counts = {}
        for video in videos:
            status = video.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print("📈 Current video status:")
        for status, count in status_counts.items():
            print(f"   {status}: {count}")
        print()
        
        # Ask user what to do
        print("🔧 CLEANUP OPTIONS:")
        print("   1. Keep all videos (just clear GCS URLs)")
        print("   2. Delete failed/pending/queued videos")
        print("   3. Delete all videos (fresh start)")
        print("   4. Cancel")
        print()
        
        choice = input("Enter your choice (1-4): ").strip()
        
        if choice == '1':
            # Clear GCS URLs but keep videos
            cleared_count = 0
            for video in videos:
                if video.gcs_url or video.thumbnail_url:
                    video.gcs_url = None
                    video.thumbnail_url = None
                    cleared_count += 1
            
            db.session.commit()
            print(f"✅ Cleared GCS URLs for {cleared_count} videos")
            
        elif choice == '2':
            # Delete failed/pending/queued videos
            videos_to_delete = Video.query.filter(
                Video.status.in_(['failed', 'pending', 'queued'])
            ).all()
            
            print(f"🗑️ Will delete {len(videos_to_delete)} videos with status: failed, pending, queued")
            confirm = input("Continue? (y/n): ").strip().lower()
            
            if confirm == 'y':
                for video in videos_to_delete:
                    db.session.delete(video)
                
                db.session.commit()
                print(f"✅ Deleted {len(videos_to_delete)} videos")
            else:
                print("❌ Deletion cancelled")
                
        elif choice == '3':
            # Delete all videos
            print(f"🗑️ Will delete ALL {len(videos)} videos")
            confirm = input("This will delete ALL videos. Type 'DELETE ALL' to confirm: ").strip()
            
            if confirm == 'DELETE ALL':
                for video in videos:
                    db.session.delete(video)
                
                db.session.commit()
                print(f"✅ Deleted all {len(videos)} videos")
            else:
                print("❌ Deletion cancelled")
                
        elif choice == '4':
            print("❌ Cleanup cancelled")
        else:
            print("❌ Invalid choice")

def verify_clean_state():
    """Verify that the bucket and database are clean"""
    print("\n🔍 ===== VERIFYING CLEAN STATE =====")
    print()
    
    # Check GCS bucket
    files = list_gcs_files()
    non_archive_files = [f for f in files if not f['parsed_info']['full_path'].startswith('archive/')]
    
    print(f"📁 GCS BUCKET:")
    print(f"   Total files: {len(files)}")
    print(f"   Non-archive files: {len(non_archive_files)}")
    
    if non_archive_files:
        print("   ⚠️ Found non-archive files:")
        for file_info in non_archive_files[:5]:
            print(f"     - {file_info['name']}")
        if len(non_archive_files) > 5:
            print(f"     ... and {len(non_archive_files) - 5} more")
    else:
        print("   ✅ No non-archive files found")
    print()
    
    # Check database
    app = create_app()
    with app.app_context():
        videos = Video.query.all()
        
        print(f"📊 DATABASE:")
        print(f"   Total videos: {len(videos)}")
        
        videos_with_gcs = [v for v in videos if v.gcs_url]
        print(f"   Videos with GCS URLs: {len(videos_with_gcs)}")
        
        if videos_with_gcs:
            print("   ⚠️ Videos still have GCS URLs:")
            for video in videos_with_gcs[:3]:
                print(f"     - Video {video.id}: {video.gcs_url[:50]}...")
            if len(videos_with_gcs) > 3:
                print(f"     ... and {len(videos_with_gcs) - 3} more")
        else:
            print("   ✅ No videos have GCS URLs")
        print()

def show_archive_info(archive_timestamp):
    """Show information about the archive"""
    print("\n📦 ===== ARCHIVE INFORMATION =====")
    print()
    
    bucket_name = get_gcs_bucket_name()
    archive_path = f"archive/{archive_timestamp}/"
    
    print(f"📁 Archive Location: gs://{bucket_name}/{archive_path}")
    print(f"📅 Archive Date: {archive_timestamp}")
    print()
    
    # List archived files
    files = list_gcs_files(prefix=archive_path)
    
    if files:
        print(f"📦 Archived Files: {len(files)}")
        
        # Count by type
        videos = [f for f in files if f['parsed_info']['full_path'].endswith('.mp4')]
        thumbnails = [f for f in files if f['parsed_info']['full_path'].endswith('.jpg')]
        
        print(f"   Videos: {len(videos)}")
        print(f"   Thumbnails: {len(thumbnails)}")
        print()
        
        # Show examples
        print("📁 Example archived files:")
        for i, file_info in enumerate(files[:10]):
            relative_path = file_info['parsed_info']['full_path'].replace(archive_path, '')
            print(f"   {i+1}. {relative_path}")
        if len(files) > 10:
            print(f"   ... and {len(files) - 10} more")
    else:
        print("❌ No archived files found")

def main():
    """Main function"""
    print("🚀 Starting Archive and Cleanup Process...")
    print()
    print("⚠️ WARNING: This will move ALL existing files to an archive folder")
    print("   and clean up the database to prepare for fresh video generation.")
    print()
    
    confirm = input("Do you want to continue? Type 'YES' to proceed: ").strip()
    
    if confirm != 'YES':
        print("❌ Operation cancelled")
        return
    
    try:
        # Step 1: Archive all existing files
        archive_timestamp = archive_all_existing_files()
        
        if not archive_timestamp:
            print("❌ Failed to create archive")
            return
        
        # Step 2: Clean database records
        clean_database_records()
        
        # Step 3: Verify clean state
        verify_clean_state()
        
        # Step 4: Show archive information
        show_archive_info(archive_timestamp)
        
        print("\n✅ Archive and cleanup complete!")
        print("\n🎯 NEXT STEPS:")
        print("   1. Your app is now ready for fresh video generation")
        print("   2. New videos will use the organized naming structure")
        print("   3. Old files are safely archived in GCS")
        print("   4. You can restore from archive if needed")
        
    except Exception as e:
        print(f"❌ Error during archive process: {e}")
        import traceback
        print(f"❌ Full traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    main() 