#!/usr/bin/env python3
"""
Video Records Review and Update Script

This script helps review and update existing video records in the database
before migrating GCS structure. It allows you to verify prompts, titles,
descriptions, and URLs for all videos.
"""

import os
import sys
from datetime import datetime, timezone

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app, db
from app.models import Video, User
from app.gcs_utils import list_gcs_files, parse_gcs_filename

def get_gcs_video_files():
    """Get all video files from GCS bucket"""
    files = list_gcs_files()
    video_files = []
    
    for file_info in files:
        parsed = file_info['parsed_info']
        path_parts = parsed.get('path_parts', [])
        
        # Check if it's a video file
        if (len(path_parts) >= 1 and 
            path_parts[0] == 'videos' and 
            parsed['extension'] == 'mp4'):
            video_files.append(file_info)
    
    return video_files

def get_gcs_thumbnail_files():
    """Get all thumbnail files from GCS bucket"""
    files = list_gcs_files()
    thumbnail_files = []
    
    for file_info in files:
        parsed = file_info['parsed_info']
        path_parts = parsed.get('path_parts', [])
        
        # Check if it's a thumbnail file
        if (len(path_parts) >= 1 and 
            path_parts[0] == 'thumbnails' and 
            parsed['extension'] == 'jpg'):
            thumbnail_files.append(file_info)
    
    return thumbnail_files

def extract_video_id_from_filename(filename):
    """Extract video ID from filename"""
    # Remove extension
    name = filename.replace('.mp4', '').replace('.jpg', '')
    
    # Try to extract numeric ID
    try:
        # If it's a simple numeric ID
        return int(name)
    except ValueError:
        # If it's a complex ID (like from Veo API)
        # Look for numeric parts
        import re
        numbers = re.findall(r'\d+', name)
        if numbers:
            return int(numbers[0])
        return None

def review_video_records():
    """Review all video records in the database"""
    print("🔍 ===== VIDEO RECORDS REVIEW =====")
    print(f"📅 Review Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print()
    
    app = create_app()
    with app.app_context():
        # Get all videos from database
        db_videos = Video.query.all()
        
        print(f"📊 DATABASE VIDEOS: {len(db_videos)}")
        print()
        
        # Get GCS files
        gcs_videos = get_gcs_video_files()
        gcs_thumbnails = get_gcs_thumbnail_files()
        
        print(f"📁 GCS FILES:")
        print(f"   Videos: {len(gcs_videos)}")
        print(f"   Thumbnails: {len(gcs_thumbnails)}")
        print()
        
        # Create mapping of video IDs to GCS files
        gcs_video_map = {}
        for file_info in gcs_videos:
            video_id = extract_video_id_from_filename(file_info['parsed_info']['filename'])
            if video_id:
                gcs_video_map[video_id] = file_info
        
        gcs_thumbnail_map = {}
        for file_info in gcs_thumbnails:
            video_id = extract_video_id_from_filename(file_info['parsed_info']['filename'])
            if video_id:
                gcs_thumbnail_map[video_id] = file_info
        
        # Review each video
        issues = []
        for video in db_videos:
            print(f"🎬 VIDEO {video.id}:")
            print(f"   Status: {video.status}")
            print(f"   Prompt: {video.prompt[:100]}{'...' if len(video.prompt) > 100 else ''}")
            print(f"   Title: {video.title or 'No title'}")
            print(f"   Description: {video.description[:100] if video.description else 'No description'}{'...' if video.description and len(video.description) > 100 else ''}")
            print(f"   Quality: {video.quality}")
            print(f"   GCS URL: {video.gcs_url or 'No GCS URL'}")
            print(f"   Thumbnail URL: {video.thumbnail_url or 'No thumbnail URL'}")
            
            # Check if video file exists in GCS
            if video.id in gcs_video_map:
                gcs_file = gcs_video_map[video.id]
                print(f"   ✅ GCS Video: {gcs_file['name']}")
            else:
                print(f"   ❌ Missing GCS video file")
                issues.append(f"Video {video.id}: Missing GCS video file")
            
            # Check if thumbnail exists in GCS
            if video.id in gcs_thumbnail_map:
                gcs_thumb = gcs_thumbnail_map[video.id]
                print(f"   ✅ GCS Thumbnail: {gcs_thumb['name']}")
            else:
                print(f"   ❌ Missing GCS thumbnail file")
                issues.append(f"Video {video.id}: Missing GCS thumbnail file")
            
            print()
        
        if issues:
            print("⚠️ ISSUES FOUND:")
            for issue in issues:
                print(f"   {issue}")
            print()
        
        return db_videos, gcs_video_map, gcs_thumbnail_map

def update_video_record(video_id):
    """Update a specific video record"""
    app = create_app()
    with app.app_context():
        video = Video.query.get(video_id)
        if not video:
            print(f"❌ Video {video_id} not found in database")
            return False
        
        print(f"✏️ UPDATING VIDEO {video_id}")
        print(f"Current values:")
        print(f"   Prompt: {video.prompt}")
        print(f"   Title: {video.title}")
        print(f"   Description: {video.description}")
        print(f"   Quality: {video.quality}")
        print(f"   GCS URL: {video.gcs_url}")
        print(f"   Thumbnail URL: {video.thumbnail_url}")
        print()
        
        # Get user input for updates
        print("Enter new values (press Enter to keep current value):")
        
        new_prompt = input(f"Prompt [{video.prompt}]: ").strip()
        if new_prompt:
            video.prompt = new_prompt
        
        new_title = input(f"Title [{video.title or ''}]: ").strip()
        if new_title:
            video.title = new_title
        
        new_description = input(f"Description [{video.description or ''}]: ").strip()
        if new_description:
            video.description = new_description
        
        new_quality = input(f"Quality [{video.quality}]: ").strip()
        if new_quality:
            video.quality = new_quality
        
        # Update GCS URLs if needed
        gcs_videos = get_gcs_video_files()
        gcs_thumbnails = get_gcs_thumbnail_files()
        
        # Find matching video file
        video_file = None
        for file_info in gcs_videos:
            if extract_video_id_from_filename(file_info['parsed_info']['filename']) == video_id:
                video_file = file_info
                break
        
        if video_file:
            new_gcs_url = f"gs://{file_info['parsed_info']['bucket_name']}/{file_info['parsed_info']['full_path']}"
            print(f"Found GCS video: {new_gcs_url}")
            update_gcs = input(f"Update GCS URL to: {new_gcs_url}? (y/n): ").strip().lower()
            if update_gcs == 'y':
                video.gcs_url = new_gcs_url
        
        # Find matching thumbnail file
        thumbnail_file = None
        for file_info in gcs_thumbnails:
            if extract_video_id_from_filename(file_info['parsed_info']['filename']) == video_id:
                thumbnail_file = file_info
                break
        
        if thumbnail_file:
            new_thumbnail_url = f"gs://{file_info['parsed_info']['bucket_name']}/{file_info['parsed_info']['full_path']}"
            print(f"Found GCS thumbnail: {new_thumbnail_url}")
            update_thumb = input(f"Update thumbnail URL to: {new_thumbnail_url}? (y/n): ").strip().lower()
            if update_thumb == 'y':
                video.thumbnail_url = new_thumbnail_url
        
        # Save changes
        try:
            db.session.commit()
            print(f"✅ Video {video_id} updated successfully")
            return True
        except Exception as e:
            print(f"❌ Error updating video {video_id}: {e}")
            db.session.rollback()
            return False

def batch_update_gcs_urls():
    """Batch update GCS URLs for all videos"""
    print("🔄 ===== BATCH UPDATE GCS URLS =====")
    print()
    
    app = create_app()
    with app.app_context():
        videos = Video.query.all()
        gcs_videos = get_gcs_video_files()
        gcs_thumbnails = get_gcs_thumbnail_files()
        
        updated_count = 0
        error_count = 0
        
        for video in videos:
            try:
                # Find matching video file
                video_file = None
                for file_info in gcs_videos:
                    if extract_video_id_from_filename(file_info['parsed_info']['filename']) == video.id:
                        video_file = file_info
                        break
                
                if video_file:
                    new_gcs_url = f"gs://{video_file['parsed_info']['bucket_name']}/{video_file['parsed_info']['full_path']}"
                    if video.gcs_url != new_gcs_url:
                        video.gcs_url = new_gcs_url
                        print(f"✅ Updated video {video.id} GCS URL")
                        updated_count += 1
                
                # Find matching thumbnail file
                thumbnail_file = None
                for file_info in gcs_thumbnails:
                    if extract_video_id_from_filename(file_info['parsed_info']['filename']) == video.id:
                        thumbnail_file = file_info
                        break
                
                if thumbnail_file:
                    new_thumbnail_url = f"gs://{thumbnail_file['parsed_info']['bucket_name']}/{thumbnail_file['parsed_info']['full_path']}"
                    if video.thumbnail_url != new_thumbnail_url:
                        video.thumbnail_url = new_thumbnail_url
                        print(f"✅ Updated video {video.id} thumbnail URL")
                        updated_count += 1
                
            except Exception as e:
                print(f"❌ Error updating video {video.id}: {e}")
                error_count += 1
        
        try:
            db.session.commit()
            print(f"\n📊 Batch Update Summary:")
            print(f"   ✅ Updated: {updated_count}")
            print(f"   ❌ Errors: {error_count}")
        except Exception as e:
            print(f"❌ Error committing changes: {e}")
            db.session.rollback()

def show_video_summary():
    """Show summary of all videos"""
    print("📊 ===== VIDEO SUMMARY =====")
    print()
    
    app = create_app()
    with app.app_context():
        videos = Video.query.all()
        
        # Count by status
        status_counts = {}
        quality_counts = {}
        gcs_url_count = 0
        thumbnail_url_count = 0
        
        for video in videos:
            status = video.status
            status_counts[status] = status_counts.get(status, 0) + 1
            
            quality = video.quality or 'unknown'
            quality_counts[quality] = quality_counts.get(quality, 0) + 1
            
            if video.gcs_url:
                gcs_url_count += 1
            
            if video.thumbnail_url:
                thumbnail_url_count += 1
        
        print(f"📊 STATISTICS:")
        print(f"   Total videos: {len(videos)}")
        print(f"   Videos with GCS URLs: {gcs_url_count}")
        print(f"   Videos with thumbnail URLs: {thumbnail_url_count}")
        print()
        
        print(f"📈 BY STATUS:")
        for status, count in status_counts.items():
            print(f"   {status}: {count}")
        print()
        
        print(f"🎬 BY QUALITY:")
        for quality, count in quality_counts.items():
            print(f"   {quality}: {count}")
        print()

def main():
    """Main function"""
    print("🚀 Starting Video Records Review...")
    print()
    
    try:
        while True:
            print("🔧 OPTIONS:")
            print("   1. Review all video records")
            print("   2. Update specific video record")
            print("   3. Batch update GCS URLs")
            print("   4. Show video summary")
            print("   5. Exit")
            print()
            
            choice = input("Enter your choice (1-5): ").strip()
            
            if choice == '1':
                review_video_records()
            elif choice == '2':
                video_id = input("Enter video ID to update: ").strip()
                try:
                    update_video_record(int(video_id))
                except ValueError:
                    print("❌ Invalid video ID")
            elif choice == '3':
                confirm = input("This will update GCS URLs for all videos. Continue? (y/n): ").strip().lower()
                if confirm == 'y':
                    batch_update_gcs_urls()
            elif choice == '4':
                show_video_summary()
            elif choice == '5':
                print("👋 Goodbye!")
                break
            else:
                print("❌ Invalid choice")
            
            print()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(f"❌ Full traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    main() 