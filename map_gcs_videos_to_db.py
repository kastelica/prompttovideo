#!/usr/bin/env python3
"""
Map existing GCS MP4 files to database video records.
Scans the bucket and matches files to videos based on ID patterns.
"""

import os
import sys
import re
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
from app.gcs_utils import list_gcs_files, get_file_info_from_gcs

def scan_gcs_for_videos():
    """Scan GCS bucket for all MP4 files and organize them by video ID."""
    print("🔍 SCANNING GCS BUCKET FOR VIDEOS")
    print("=" * 50)
    
    # Scan different paths in the bucket
    paths_to_scan = [
        'videos/',  # Organized videos
        'archive/videos/',  # Archived videos
        '',  # Root level (in case there are files there)
    ]
    
    all_video_files = {}
    
    for path in paths_to_scan:
        print(f"\n📁 Scanning path: {path}")
        try:
            files = list_gcs_files(prefix=path, max_results=1000)
            mp4_files = [f for f in files if f['name'].endswith('.mp4')]
            print(f"   Found {len(mp4_files)} MP4 files")
            
            for file_info in mp4_files:
                filename = file_info['name']
                print(f"   📹 {filename}")
                
                # Try to extract video ID from filename
                video_id = extract_video_id_from_filename(filename)
                if video_id:
                    if video_id not in all_video_files:
                        all_video_files[video_id] = []
                    all_video_files[video_id].append({
                        'gcs_url': f"gs://prompt-veo-videos/{filename}",
                        'filename': filename,
                        'size': file_info['size'],
                        'updated': file_info['updated']
                    })
                    print(f"      → Mapped to Video ID: {video_id}")
                else:
                    print(f"      → Could not extract video ID")
                    
        except Exception as e:
            print(f"   ❌ Error scanning {path}: {e}")
    
    print(f"\n📊 GCS SCAN SUMMARY:")
    print(f"   Total video files found: {sum(len(files) for files in all_video_files.values())}")
    print(f"   Unique video IDs: {len(all_video_files)}")
    
    for video_id, files in all_video_files.items():
        print(f"   Video ID {video_id}: {len(files)} file(s)")
        for file_info in files:
            print(f"      - {file_info['filename']}")
    
    return all_video_files

def extract_video_id_from_filename(filename):
    """Extract video ID from various filename patterns."""
    # Remove path and get just filename
    basename = os.path.basename(filename)
    
    # Pattern 1: Organized format: videos/2025/08/free/13_bfd18b58_20250803_182209.mp4
    # Extract: 13
    match = re.search(r'/(\d+)_[a-f0-9]+_\d+_\d+\.mp4$', filename)
    if match:
        return int(match.group(1))
    
    # Pattern 2: Archive format: archive/videos/1422573394135096443/sample_0.mp4
    # Extract: 1422573394135096443
    match = re.search(r'/archive/videos/(\d+)/', filename)
    if match:
        return int(match.group(1))
    
    # Pattern 3: Simple format: videos/123.mp4
    match = re.search(r'/(\d+)\.mp4$', filename)
    if match:
        return int(match.group(1))
    
    # Pattern 4: Sample format: videos/123/sample_0.mp4
    match = re.search(r'/(\d+)/sample_0\.mp4$', filename)
    if match:
        return int(match.group(1))
    
    return None

def get_database_videos():
    """Get all videos from database that need GCS mapping."""
    app = create_app()
    
    with app.app_context():
        # Get videos that are missing GCS URLs or have missing files
        videos = Video.query.all()
        
        videos_needing_mapping = []
        for video in videos:
            needs_mapping = False
            reason = []
            
            # Check if GCS URL is missing
            if not video.gcs_url:
                needs_mapping = True
                reason.append("No GCS URL")
            else:
                # Check if GCS file exists
                file_info = get_file_info_from_gcs(video.gcs_url)
                if not file_info.get('exists'):
                    needs_mapping = True
                    reason.append("GCS file missing")
            
            if needs_mapping:
                videos_needing_mapping.append({
                    'video': video,
                    'reason': reason
                })
        
        return videos_needing_mapping

def map_videos_to_gcs_files():
    """Map database videos to GCS files."""
    print("🗺️  MAPPING VIDEOS TO GCS FILES")
    print("=" * 50)
    
    # Scan GCS for video files
    gcs_videos = scan_gcs_for_videos()
    
    # Get database videos needing mapping
    db_videos = get_database_videos()
    
    print(f"\n📊 MAPPING ANALYSIS:")
    print(f"   Videos in GCS: {len(gcs_videos)}")
    print(f"   Videos needing mapping: {len(db_videos)}")
    
    # Create mapping suggestions
    mappings = []
    unmapped_gcs = set(gcs_videos.keys())
    unmapped_db = []
    
    for db_video_info in db_videos:
        video = db_video_info['video']
        video_id = video.id
        
        if video_id in gcs_videos:
            # Found a match!
            gcs_files = gcs_videos[video_id]
            # Use the most recent file if multiple exist
            best_file = max(gcs_files, key=lambda x: x['updated'])
            
            mappings.append({
                'video_id': video_id,
                'prompt': video.prompt,
                'current_gcs_url': video.gcs_url,
                'new_gcs_url': best_file['gcs_url'],
                'filename': best_file['filename'],
                'reason': db_video_info['reason']
            })
            
            unmapped_gcs.discard(video_id)
            print(f"   ✅ Video {video_id}: {video.prompt[:40]}... → {best_file['filename']}")
        else:
            unmapped_db.append({
                'video_id': video_id,
                'prompt': video.prompt,
                'reason': db_video_info['reason']
            })
            print(f"   ❌ Video {video_id}: {video.prompt[:40]}... → No GCS file found")
    
    print(f"\n📊 MAPPING SUMMARY:")
    print(f"   Videos that can be mapped: {len(mappings)}")
    print(f"   Videos without GCS files: {len(unmapped_db)}")
    print(f"   GCS files without DB records: {len(unmapped_gcs)}")
    
    if unmapped_gcs:
        print(f"\n🗂️  UNMAPPED GCS FILES:")
        for video_id in unmapped_gcs:
            files = gcs_videos[video_id]
            print(f"   Video ID {video_id}: {len(files)} file(s)")
            for file_info in files:
                print(f"      - {file_info['filename']}")
    
    return mappings, unmapped_db, unmapped_gcs

def apply_video_mappings(mappings):
    """Apply the video mappings to the database."""
    if not mappings:
        print("✅ No mappings to apply")
        return
    
    print(f"\n🔧 APPLYING {len(mappings)} VIDEO MAPPINGS")
    print("=" * 50)
    
    app = create_app()
    
    with app.app_context():
        success_count = 0
        error_count = 0
        
        for mapping in mappings:
            try:
                video = Video.query.get(mapping['video_id'])
                if not video:
                    print(f"❌ Video ID {mapping['video_id']} not found in database")
                    error_count += 1
                    continue
                
                print(f"\n🎬 Updating Video ID {mapping['video_id']}: {mapping['prompt'][:40]}...")
                print(f"   Old GCS URL: {mapping['current_gcs_url']}")
                print(f"   New GCS URL: {mapping['new_gcs_url']}")
                
                # Update the video record
                video.gcs_url = mapping['new_gcs_url']
                db.session.commit()
                
                print(f"   ✅ Database updated successfully")
                success_count += 1
                
            except Exception as e:
                print(f"   ❌ Error updating video {mapping['video_id']}: {e}")
                error_count += 1
                db.session.rollback()
        
        print(f"\n📊 UPDATE SUMMARY:")
        print(f"   Successfully updated: {success_count}")
        print(f"   Errors: {error_count}")

def interactive_mapping():
    """Interactive mapping with user confirmation."""
    print("🎯 INTERACTIVE VIDEO MAPPING")
    print("=" * 40)
    
    # Get mappings
    mappings, unmapped_db, unmapped_gcs = map_videos_to_gcs_files()
    
    if not mappings:
        print("✅ No videos need mapping")
        return
    
    print(f"\n🔍 MAPPING PREVIEW:")
    for i, mapping in enumerate(mappings, 1):
        print(f"\n{i}. Video ID {mapping['video_id']}: {mapping['prompt'][:50]}...")
        print(f"   Current: {mapping['current_gcs_url'] or 'None'}")
        print(f"   New: {mapping['new_gcs_url']}")
        print(f"   File: {mapping['filename']}")
        print(f"   Reason: {', '.join(mapping['reason'])}")
    
    response = input(f"\n🗺️  Apply {len(mappings)} video mappings? (y/N): ").strip()
    if response.lower() == 'y':
        apply_video_mappings(mappings)
        print("\n✅ Mapping completed!")
    else:
        print("❌ Mapping cancelled")

def main():
    """Main menu for video mapping."""
    while True:
        print("\n🗺️  GCS VIDEO MAPPING TOOL")
        print("=" * 40)
        print("1. Scan GCS bucket for videos")
        print("2. Show mapping analysis")
        print("3. Interactive mapping")
        print("4. Exit")
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == '1':
            scan_gcs_for_videos()
        elif choice == '2':
            map_videos_to_gcs_files()
        elif choice == '3':
            interactive_mapping()
        elif choice == '4':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid option")

if __name__ == "__main__":
    main() 