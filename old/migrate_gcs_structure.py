#!/usr/bin/env python3
"""
GCS Structure Migration Script

This script helps migrate existing files to the new organized structure
and generates missing thumbnails.
"""

import os
import sys
from datetime import datetime, timezone

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app, db
from app.models import Video
from app.gcs_utils import (
    list_gcs_files, parse_gcs_filename, get_gcs_bucket_name,
    generate_video_filename, generate_thumbnail_filename
)
from app.tasks import generate_video_thumbnail_from_gcs
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

def migrate_video_files():
    """Migrate existing video files to organized structure"""
    print("🔄 ===== MIGRATING VIDEO FILES =====")
    print()
    
    # Get all files in the bucket
    files = list_gcs_files()
    
    # Filter for legacy video files
    legacy_videos = []
    for file_info in files:
        parsed = file_info['parsed_info']
        path_parts = parsed.get('path_parts', [])
        
        # Check if it's a legacy video file
        if (len(path_parts) >= 1 and 
            path_parts[0] == 'videos' and 
            not parsed['is_organized'] and 
            parsed['extension'] == 'mp4'):
            legacy_videos.append(file_info)
    
    print(f"📁 Found {len(legacy_videos)} legacy video files to migrate")
    
    if not legacy_videos:
        print("✅ No legacy video files to migrate")
        return
    
    # Get database videos to match with
    app = create_app()
    with app.app_context():
        db_videos = {v.id: v for v in Video.query.all()}
        
        migrated_count = 0
        error_count = 0
        
        for file_info in legacy_videos:
            try:
                # Extract video ID from filename
                filename = file_info['parsed_info']['filename']
                video_id_str = filename.replace('.mp4', '')
                
                try:
                    video_id = int(video_id_str)
                except ValueError:
                    print(f"⚠️ Skipping file with non-numeric ID: {filename}")
                    continue
                
                # Check if video exists in database
                if video_id not in db_videos:
                    print(f"⚠️ Video {video_id} not found in database, skipping")
                    continue
                
                video = db_videos[video_id]
                
                print(f"🔄 Migrating video {video_id}: {video.prompt[:50]}...")
                
                # Generate new organized path
                new_path, new_filename, new_gcs_url = generate_video_filename(
                    video_id=video_id,
                    quality=video.quality,
                    prompt=video.prompt,
                    user_id=video.user_id
                )
                
                # Move file in GCS
                success = move_gcs_file(
                    old_path=file_info['parsed_info']['full_path'],
                    new_path=new_path,
                    bucket_name=file_info['parsed_info']['bucket_name']
                )
                
                if success:
                    # Update database record
                    video.gcs_url = new_gcs_url
                    db.session.commit()
                    
                    print(f"✅ Migrated to: {new_path}")
                    migrated_count += 1
                else:
                    print(f"❌ Failed to migrate video {video_id}")
                    error_count += 1
                    
            except Exception as e:
                print(f"❌ Error migrating file {file_info['name']}: {e}")
                error_count += 1
        
        print(f"\n📊 Migration Summary:")
        print(f"   ✅ Successfully migrated: {migrated_count}")
        print(f"   ❌ Errors: {error_count}")
        print(f"   📁 Total processed: {len(legacy_videos)}")

def generate_missing_thumbnails():
    """Generate thumbnails for videos that don't have them"""
    print("\n🖼️ ===== GENERATING MISSING THUMBNAILS =====")
    print()
    
    app = create_app()
    with app.app_context():
        from sqlalchemy import or_, not_
        
        # Get videos with GCS URLs but no thumbnails
        videos_without_thumbnails = Video.query.filter(
            Video.status == 'completed',
            Video.gcs_url.isnot(None),
            Video.gcs_url.startswith('gs://'),
            or_(
                Video.thumbnail_url.is_(None),
                Video.thumbnail_url == '',
                not_(Video.thumbnail_url.startswith('gs://'))
            )
        ).all()
        
        print(f"📁 Found {len(videos_without_thumbnails)} videos without GCS thumbnails")
        
        if not videos_without_thumbnails:
            print("✅ All videos have thumbnails")
            return
        
        generated_count = 0
        error_count = 0
        
        for video in videos_without_thumbnails:
            try:
                print(f"🖼️ Generating thumbnail for video {video.id}: {video.prompt[:50]}...")
                
                # Generate thumbnail
                thumbnail_url = generate_video_thumbnail_from_gcs(
                    gcs_url=video.gcs_url,
                    video_id=video.id,
                    quality=video.quality,
                    prompt=video.prompt
                )
                
                if thumbnail_url:
                    # Update database
                    video.thumbnail_url = thumbnail_url
                    db.session.commit()
                    
                    print(f"✅ Thumbnail generated: {thumbnail_url}")
                    generated_count += 1
                else:
                    print(f"❌ Failed to generate thumbnail for video {video.id}")
                    error_count += 1
                    
            except Exception as e:
                print(f"❌ Error generating thumbnail for video {video.id}: {e}")
                error_count += 1
                db.session.rollback()
        
        print(f"\n📊 Thumbnail Generation Summary:")
        print(f"   ✅ Successfully generated: {generated_count}")
        print(f"   ❌ Errors: {error_count}")
        print(f"   📁 Total processed: {len(videos_without_thumbnails)}")

def move_gcs_file(old_path, new_path, bucket_name):
    """Move a file within GCS bucket"""
    try:
        storage_client = get_gcs_client()
        bucket = storage_client.bucket(bucket_name)
        
        # Get source blob
        source_blob = bucket.blob(old_path)
        
        if not source_blob.exists():
            print(f"❌ Source file not found: {old_path}")
            return False
        
        # Copy to new location
        new_blob = bucket.blob(new_path)
        bucket.copy_blob(source_blob, bucket, new_blob.name)
        
        # Delete old file
        source_blob.delete()
        
        print(f"✅ Moved {old_path} -> {new_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error moving file {old_path}: {e}")
        return False

def cleanup_orphaned_files():
    """Clean up orphaned files that don't have database records"""
    print("\n🧹 ===== CLEANING UP ORPHANED FILES =====")
    print()
    
    # Get all files in bucket
    files = list_gcs_files()
    
    # Get database video IDs
    app = create_app()
    with app.app_context():
        db_video_ids = {v.id for v in Video.query.all()}
        
        orphaned_files = []
        
        for file_info in files:
            parsed = file_info['parsed_info']
            path_parts = parsed.get('path_parts', [])
            
            # Check if it's a video file
            if (len(path_parts) >= 1 and 
                path_parts[0] == 'videos' and 
                parsed['extension'] == 'mp4'):
                # Extract video ID from filename
                filename = parsed['filename']
                video_id_str = filename.replace('.mp4', '')
                
                try:
                    video_id = int(video_id_str)
                    if video_id not in db_video_ids:
                        orphaned_files.append(file_info)
                except ValueError:
                    # Non-numeric filename, might be orphaned
                    orphaned_files.append(file_info)
        
        print(f"📁 Found {len(orphaned_files)} potentially orphaned files")
        
        if not orphaned_files:
            print("✅ No orphaned files found")
            return
        
        # Show examples
        print("📁 Examples of orphaned files:")
        for i, file_info in enumerate(orphaned_files[:10]):
            print(f"   {i+1}. {file_info['name']} ({file_info['size']} bytes)")
        
        if len(orphaned_files) > 10:
            print(f"   ... and {len(orphaned_files) - 10} more")
        
        print("\n⚠️ WARNING: These files will be permanently deleted!")
        response = input("Do you want to proceed with deletion? (yes/no): ")
        
        if response.lower() != 'yes':
            print("❌ Deletion cancelled")
            return
        
        # Delete orphaned files
        deleted_count = 0
        error_count = 0
        
        for file_info in orphaned_files:
            try:
                storage_client = get_gcs_client()
                bucket = storage_client.bucket(file_info['parsed_info']['bucket_name'])
                blob = bucket.blob(file_info['parsed_info']['full_path'])
                
                if blob.exists():
                    blob.delete()
                    print(f"🗑️ Deleted: {file_info['name']}")
                    deleted_count += 1
                else:
                    print(f"⚠️ File not found: {file_info['name']}")
                    
            except Exception as e:
                print(f"❌ Error deleting {file_info['name']}: {e}")
                error_count += 1
        
        print(f"\n📊 Cleanup Summary:")
        print(f"   🗑️ Deleted: {deleted_count}")
        print(f"   ❌ Errors: {error_count}")
        print(f"   📁 Total processed: {len(orphaned_files)}")

def show_migration_preview():
    """Show preview of what will be migrated"""
    print("👀 ===== MIGRATION PREVIEW =====")
    print()
    
    # Get all files
    files = list_gcs_files()
    
    # Analyze current structure
    legacy_videos = []
    legacy_thumbnails = []
    organized_files = []
    
    for file_info in files:
        parsed = file_info['parsed_info']
        path_parts = parsed.get('path_parts', [])
        
        if parsed['is_organized']:
            organized_files.append(file_info)
        elif len(path_parts) >= 1 and path_parts[0] == 'videos':
            legacy_videos.append(file_info)
        elif len(path_parts) >= 1 and path_parts[0] == 'thumbnails':
            legacy_thumbnails.append(file_info)
    
    print("📊 CURRENT STRUCTURE:")
    print(f"   Legacy videos: {len(legacy_videos)}")
    print(f"   Legacy thumbnails: {len(legacy_thumbnails)}")
    print(f"   Organized files: {len(organized_files)}")
    print()
    
    # Show examples of what will be migrated
    if legacy_videos:
        print("📁 LEGACY VIDEOS TO MIGRATE:")
        for i, file_info in enumerate(legacy_videos[:5]):
            print(f"   {i+1}. {file_info['name']}")
        if len(legacy_videos) > 5:
            print(f"   ... and {len(legacy_videos) - 5} more")
        print()
    
    if legacy_thumbnails:
        print("📁 LEGACY THUMBNAILS TO MIGRATE:")
        for i, file_info in enumerate(legacy_thumbnails[:5]):
            print(f"   {i+1}. {file_info['name']}")
        if len(legacy_thumbnails) > 5:
            print(f"   ... and {len(legacy_thumbnails) - 5} more")
        print()
    
    # Check for missing thumbnails
    app = create_app()
    with app.app_context():
        from sqlalchemy import or_, not_
        
        videos_without_thumbnails = Video.query.filter(
            Video.status == 'completed',
            Video.gcs_url.isnot(None),
            Video.gcs_url.startswith('gs://'),
            or_(
                Video.thumbnail_url.is_(None),
                Video.thumbnail_url == '',
                not_(Video.thumbnail_url.startswith('gs://'))
            )
        ).count()
        
        print(f"🖼️ VIDEOS NEEDING THUMBNAILS: {videos_without_thumbnails}")
        print()

def main():
    """Main migration function"""
    print("🚀 Starting GCS Structure Migration...")
    print()
    
    try:
        # Show preview first
        show_migration_preview()
        
        # Ask user what to do
        print("🔧 MIGRATION OPTIONS:")
        print("   1. Preview only (what we just did)")
        print("   2. Migrate video files to organized structure")
        print("   3. Generate missing thumbnails")
        print("   4. Clean up orphaned files")
        print("   5. Run all migrations")
        print("   6. Exit")
        print()
        
        choice = input("Enter your choice (1-6): ")
        
        if choice == '1':
            print("✅ Preview complete")
        elif choice == '2':
            migrate_video_files()
        elif choice == '3':
            generate_missing_thumbnails()
        elif choice == '4':
            cleanup_orphaned_files()
        elif choice == '5':
            migrate_video_files()
            generate_missing_thumbnails()
            cleanup_orphaned_files()
        elif choice == '6':
            print("👋 Goodbye!")
        else:
            print("❌ Invalid choice")
        
        print("\n✅ Migration process complete!")
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        import traceback
        print(f"❌ Full traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    main() 