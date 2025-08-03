#!/usr/bin/env python3
"""
Simple video mapping - map found GCS files to database records.
"""

import os
import sys
import re

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

# Based on the scan results, here are the GCS files we found
GCS_VIDEO_FILES = {
    # Organized videos (preferred)
    11: "gs://prompt-veo-videos/videos/2025/08/free/11_dbb14b16_20250803_175549.mp4",
    12: "gs://prompt-veo-videos/videos/2025/08/free/12_6efe7634_20250803_181425.mp4",
    13: "gs://prompt-veo-videos/videos/2025/08/free/13_bfd18b58_20250803_182209.mp4",
    14: "gs://prompt-veo-videos/videos/2025/08/free/14_a2d92315_20250803_183144.mp4",
    27: "gs://prompt-veo-videos/videos/2025/08/free/27_dc419855_20250803_055142.mp4",
    29: "gs://prompt-veo-videos/videos/2025/08/free/29_32664357_20250803_191300.mp4",
    31: "gs://prompt-veo-videos/videos/2025/08/free/31_501e20b4_20250803_192451.mp4",
    
    # Archive videos
    2: "gs://prompt-veo-videos/archive/20250803_050844/videos/2.mp4",
    4: "gs://prompt-veo-videos/archive/20250803_050844/videos/4.mp4",
    6: "gs://prompt-veo-videos/archive/20250803_050844/videos/6.mp4",
    10: "gs://prompt-veo-videos/archive/20250803_050844/videos/10.mp4",
    15: "gs://prompt-veo-videos/archive/20250803_050844/videos/15.mp4",
    16: "gs://prompt-veo-videos/archive/20250803_050844/videos/16.mp4",
    61: "gs://prompt-veo-videos/archive/20250803_050844/videos/61.mp4",
    
    # Large ID videos from archive
    1166575668786923349: "gs://prompt-veo-videos/archive/20250803_050844/videos/1166575668786923349/sample_0.mp4",
    1422573394135096443: "gs://prompt-veo-videos/archive/20250803_050844/videos/1422573394135096443/sample_0.mp4",
    2418485289036200076: "gs://prompt-veo-videos/archive/20250803_050844/videos/2418485289036200076/sample_0.mp4",
    3408840530871288378: "gs://prompt-veo-videos/archive/20250803_050844/videos/3408840530871288378/sample_0.mp4",
    4333248414357645713: "gs://prompt-veo-videos/archive/20250803_050844/videos/4333248414357645713/sample_0.mp4",
    6085687816516152312: "gs://prompt-veo-videos/archive/20250803_050844/videos/6085687816516152312/sample_0.mp4",
    6385391778595382911: "gs://prompt-veo-videos/archive/20250803_050844/videos/6385391778595382911/sample_0.mp4",
    8781296985594815621: "gs://prompt-veo-videos/archive/20250803_050844/videos/8781296985594815621/sample_0.mp4",
}

def map_videos_to_gcs():
    """Map database videos to the found GCS files."""
    app = create_app()
    
    with app.app_context():
        print("🗺️  MAPPING VIDEOS TO GCS FILES")
        print("=" * 50)
        
        # Get all videos from database
        all_videos = Video.query.all()
        print(f"📊 Total videos in database: {len(all_videos)}")
        
        mappings = []
        unmapped_videos = []
        
        for video in all_videos:
            video_id = video.id
            
            if video_id in GCS_VIDEO_FILES:
                new_gcs_url = GCS_VIDEO_FILES[video_id]
                current_gcs_url = video.gcs_url
                
                mappings.append({
                    'video_id': video_id,
                    'prompt': video.prompt,
                    'current_gcs_url': current_gcs_url,
                    'new_gcs_url': new_gcs_url,
                    'status': video.status
                })
                
                print(f"   ✅ Video {video_id}: {video.prompt[:40]}...")
                print(f"      Current: {current_gcs_url or 'None'}")
                print(f"      New: {new_gcs_url}")
            else:
                unmapped_videos.append({
                    'video_id': video_id,
                    'prompt': video.prompt,
                    'current_gcs_url': video.gcs_url,
                    'status': video.status
                })
                print(f"   ❌ Video {video_id}: {video.prompt[:40]}... → No GCS file found")
        
        print(f"\n📊 MAPPING SUMMARY:")
        print(f"   Videos that can be mapped: {len(mappings)}")
        print(f"   Videos without GCS files: {len(unmapped_videos)}")
        
        return mappings, unmapped_videos

def apply_mappings(mappings):
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

def show_mapping_preview():
    """Show a preview of what would be mapped."""
    mappings, unmapped_videos = map_videos_to_gcs()
    
    if not mappings:
        print("✅ No videos need mapping")
        return
    
    print(f"\n🔍 MAPPING PREVIEW:")
    print(f"   {len(mappings)} videos can be mapped to GCS files")
    
    for i, mapping in enumerate(mappings, 1):
        print(f"\n{i}. Video ID {mapping['video_id']}: {mapping['prompt'][:50]}...")
        print(f"   Status: {mapping['status']}")
        print(f"   Current: {mapping['current_gcs_url'] or 'None'}")
        print(f"   New: {mapping['new_gcs_url']}")
    
    if unmapped_videos:
        print(f"\n❌ {len(unmapped_videos)} VIDEOS WITHOUT GCS FILES:")
        for video in unmapped_videos[:10]:  # Show first 10
            print(f"   ID {video['video_id']}: {video['prompt'][:40]}... (Status: {video['status']})")
        if len(unmapped_videos) > 10:
            print(f"   ... and {len(unmapped_videos) - 10} more")

def interactive_mapping():
    """Interactive mapping with user confirmation."""
    print("🎯 INTERACTIVE VIDEO MAPPING")
    print("=" * 40)
    
    mappings, unmapped_videos = map_videos_to_gcs()
    
    if not mappings:
        print("✅ No videos need mapping")
        return
    
    show_mapping_preview()
    
    response = input(f"\n🗺️  Apply {len(mappings)} video mappings? (y/N): ").strip()
    if response.lower() == 'y':
        apply_mappings(mappings)
        print("\n✅ Mapping completed!")
    else:
        print("❌ Mapping cancelled")

def main():
    """Main menu for video mapping."""
    while True:
        print("\n🗺️  SIMPLE VIDEO MAPPING TOOL")
        print("=" * 40)
        print("1. Show mapping preview")
        print("2. Interactive mapping")
        print("3. Exit")
        
        choice = input("\nSelect option (1-3): ").strip()
        
        if choice == '1':
            show_mapping_preview()
        elif choice == '2':
            interactive_mapping()
        elif choice == '3':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid option")

if __name__ == "__main__":
    main() 