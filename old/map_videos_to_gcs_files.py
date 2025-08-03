#!/usr/bin/env python3
"""
Map Videos to GCS Files
=======================

This script helps map database video records to actual files in the GCS archive folder.
It will show you which files in the bucket correspond to which videos in the database.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from google.cloud import storage
import re

# Database connection
DATABASE_URL = "postgresql://prompttovideo:PromptToVideo2024!@34.46.33.136:5432/prompttovideo"

def connect_to_database():
    """Connect to the production database"""
    try:
        engine = create_engine(DATABASE_URL)
        Session = sessionmaker(bind=engine)
        return engine, Session()
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return None, None

def get_videos_from_database(session):
    """Get all videos from database"""
    try:
        query = text("""
            SELECT 
                id,
                title,
                prompt,
                slug,
                gcs_url,
                gcs_signed_url,
                thumbnail_url,
                status,
                public,
                veo_job_id,
                created_at
            FROM videos 
            WHERE status = 'completed'
            ORDER BY id
        """)
        
        result = session.execute(query)
        return result.fetchall()
    except Exception as e:
        print(f"❌ Error fetching videos: {e}")
        return []

def list_gcs_archive_files(bucket_name="prompt-veo-videos"):
    """List all files in the archive folder of GCS bucket"""
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        
        # List all blobs in the archive folder
        blobs = bucket.list_blobs(prefix="archive/")
        
        archive_files = []
        for blob in blobs:
            if blob.name.endswith('.mp4'):  # Only video files
                archive_files.append({
                    'name': blob.name,
                    'size': blob.size,
                    'updated': blob.updated,
                    'path': blob.name
                })
        
        return archive_files
    except Exception as e:
        print(f"❌ Error listing GCS files: {e}")
        return []

def extract_job_id_from_gcs_url(gcs_url):
    """Extract job ID from GCS URL"""
    if not gcs_url:
        return None
    
    # Pattern: gs://bucket/videos/JOB_ID/sample_0.mp4
    # or: gs://bucket/archive/videos/JOB_ID/sample_0.mp4
    pattern = r'/(\d+)/sample_\d+\.mp4$'
    match = re.search(pattern, gcs_url)
    
    if match:
        return match.group(1)
    
    # Try other patterns
    pattern2 = r'/(\d+)\.mp4$'
    match2 = re.search(pattern2, gcs_url)
    
    if match2:
        return match2.group(1)
    
    return None

def map_videos_to_files(videos, archive_files):
    """Map database videos to GCS files"""
    print(f"\n🔍 MAPPING VIDEOS TO GCS FILES")
    print("=" * 60)
    
    # Create mapping
    mappings = []
    unmapped_videos = []
    unmapped_files = []
    
    # Track which files we've mapped
    mapped_files = set()
    
    for video in videos:
        # Extract job ID from GCS URL
        job_id = extract_job_id_from_gcs_url(video.gcs_url)
        veo_job_id = video.veo_job_id
        
        print(f"\n📹 Video ID {video.id}: '{video.title}'")
        print(f"   GCS URL: {video.gcs_url}")
        print(f"   Job ID from URL: {job_id}")
        print(f"   Veo Job ID: {veo_job_id}")
        
        # Try to find matching file
        matching_file = None
        
        # Method 1: Match by job ID in URL
        if job_id:
            for file in archive_files:
                if job_id in file['name'] and file['name'] not in mapped_files:
                    matching_file = file
                    break
        
        # Method 2: Match by Veo job ID
        if not matching_file and veo_job_id:
            for file in archive_files:
                if str(veo_job_id) in file['name'] and file['name'] not in mapped_files:
                    matching_file = file
                    break
        
        # Method 3: Match by video ID in filename
        if not matching_file:
            for file in archive_files:
                if f"/{video.id}." in file['name'] or f"/{video.id}/" in file['name']:
                    matching_file = file
                    break
        
        if matching_file:
            mappings.append({
                'video': video,
                'file': matching_file,
                'match_method': 'job_id' if job_id else 'veo_job_id' if veo_job_id else 'video_id'
            })
            mapped_files.add(matching_file['name'])
            print(f"   ✅ Mapped to: {matching_file['name']}")
            print(f"   📁 File size: {matching_file['size']} bytes")
            print(f"   📅 File updated: {matching_file['updated']}")
        else:
            unmapped_videos.append(video)
            print(f"   ❌ No matching file found")
    
    # Find unmapped files
    for file in archive_files:
        if file['name'] not in mapped_files:
            unmapped_files.append(file)
    
    return mappings, unmapped_videos, unmapped_files

def display_mapping_summary(mappings, unmapped_videos, unmapped_files):
    """Display summary of mappings"""
    print(f"\n📊 MAPPING SUMMARY")
    print("=" * 60)
    
    print(f"✅ Successfully mapped: {len(mappings)} videos")
    print(f"❌ Unmapped videos: {len(unmapped_videos)}")
    print(f"📁 Unmapped files: {len(unmapped_files)}")
    
    if unmapped_videos:
        print(f"\n❌ UNMAPPED VIDEOS:")
        print("-" * 40)
        for video in unmapped_videos:
            print(f"   ID {video.id}: '{video.title}'")
            print(f"      GCS URL: {video.gcs_url}")
            print(f"      Veo Job ID: {video.veo_job_id}")
            print()
    
    if unmapped_files:
        print(f"\n📁 UNMAPPED FILES:")
        print("-" * 40)
        for file in unmapped_files[:10]:  # Show first 10
            print(f"   {file['name']} ({file['size']} bytes)")
        
        if len(unmapped_files) > 10:
            print(f"   ... and {len(unmapped_files) - 10} more files")

def suggest_manual_mappings(unmapped_videos, unmapped_files):
    """Suggest manual mappings based on patterns"""
    print(f"\n💡 SUGGESTED MANUAL MAPPINGS")
    print("=" * 60)
    
    if not unmapped_videos or not unmapped_files:
        print("   No manual mappings needed!")
        return
    
    print("Based on file patterns, here are suggested mappings:")
    print()
    
    # Group files by pattern
    file_patterns = {}
    for file in unmapped_files:
        # Extract pattern (e.g., "videos/1234567890/" or "videos/123.mp4")
        pattern = re.sub(r'/\d+\.mp4$', '/ID.mp4', file['name'])
        pattern = re.sub(r'/\d+/sample_\d+\.mp4$', '/ID/sample_0.mp4', pattern)
        
        if pattern not in file_patterns:
            file_patterns[pattern] = []
        file_patterns[pattern].append(file)
    
    for pattern, files in file_patterns.items():
        print(f"📁 Pattern: {pattern}")
        print(f"   Files: {len(files)}")
        for file in files[:3]:  # Show first 3 files
            print(f"      {file['name']}")
        if len(files) > 3:
            print(f"      ... and {len(files) - 3} more")
        print()

def main():
    """Main mapping process"""
    print("🗺️  MAP VIDEOS TO GCS FILES")
    print("=" * 50)
    
    # Connect to database
    engine, session = connect_to_database()
    if not engine or not session:
        return
    
    try:
        # Get videos from database
        print("📊 Fetching videos from database...")
        videos = get_videos_from_database(session)
        if not videos:
            print("❌ No videos found in database")
            return
        
        print(f"✅ Found {len(videos)} completed videos")
        
        # List GCS archive files
        print("\n📁 Fetching files from GCS archive...")
        archive_files = list_gcs_archive_files()
        if not archive_files:
            print("❌ No files found in GCS archive")
            return
        
        print(f"✅ Found {len(archive_files)} video files in archive")
        
        # Map videos to files
        mappings, unmapped_videos, unmapped_files = map_videos_to_files(videos, archive_files)
        
        # Display summary
        display_mapping_summary(mappings, unmapped_videos, unmapped_files)
        
        # Suggest manual mappings
        suggest_manual_mappings(unmapped_videos, unmapped_files)
        
        # Show successful mappings
        if mappings:
            print(f"\n✅ SUCCESSFUL MAPPINGS:")
            print("-" * 40)
            for mapping in mappings[:5]:  # Show first 5
                video = mapping['video']
                file = mapping['file']
                print(f"   Video {video.id} ('{video.title}') → {file['name']}")
            
            if len(mappings) > 5:
                print(f"   ... and {len(mappings) - 5} more mappings")
        
    except Exception as e:
        print(f"❌ Error during mapping: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    main() 