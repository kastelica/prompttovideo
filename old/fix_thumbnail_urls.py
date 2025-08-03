#!/usr/bin/env python3
"""
Fix Thumbnail URLs
=================

This script updates thumbnail URLs to point to the correct archive locations
instead of using signed URLs that expire.
"""

import os
import sys
import re
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database connection
DATABASE_URL = "postgresql://prompttovideo:PromptToVideo2024!@34.46.33.136:5432/prompttovideo"

def connect_to_database():
    """Connect to the production database"""
    try:
        engine = create_engine(DATABASE_URL)
        Session = sessionmaker(bind=engine)
        return engine, Session()
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        return None, None

def get_videos_with_thumbnails(session):
    """Get videos that have thumbnail URLs"""
    try:
        query = text("""
            SELECT 
                id,
                title,
                thumbnail_url,
                gcs_url,
                status,
                public
            FROM videos 
            WHERE status = 'completed' AND thumbnail_url IS NOT NULL
            ORDER BY id
        """)
        
        result = session.execute(query)
        return result.fetchall()
    except Exception as e:
        print(f"Error fetching videos: {e}")
        return []

def extract_filename_from_url(url):
    """Extract filename from various URL formats"""
    if not url:
        return None
    
    # Handle signed URLs
    if '?' in url:
        # Remove query parameters
        url = url.split('?')[0]
    
    # Handle gs:// URLs
    if url.startswith('gs://'):
        url = url.replace('gs://prompt-veo-videos/', '')
    
    # Handle https:// URLs
    if url.startswith('https://storage.googleapis.com/prompt-veo-videos/'):
        url = url.replace('https://storage.googleapis.com/prompt-veo-videos/', '')
    
    # Extract just the filename
    if '/' in url:
        filename = url.split('/')[-1]
        return filename
    
    return url

def determine_archive_path(video_id, filename):
    """Determine the correct archive path for a thumbnail"""
    # Based on the GCS structure we saw, thumbnails are in:
    # archive/20250803_050844/thumbnails/filename.jpg
    # or archive/thumbnails/2025/08/free/filename.jpg
    
    # For now, let's use the simpler path structure
    # We'll put them in archive/thumbnails/filename
    return f"archive/thumbnails/{filename}"

def update_thumbnail_urls():
    """Update thumbnail URLs to archive locations"""
    
    # Initialize database connection
    engine, session = connect_to_database()
    if not engine or not session:
        return
    
    try:
        # Get videos with thumbnails
        print("Fetching videos with thumbnails...")
        videos = get_videos_with_thumbnails(session)
        if not videos:
            print("No videos found with thumbnails")
            return
        
        print(f"Found {len(videos)} videos with thumbnails")
        print()
        
        success_count = 0
        error_count = 0
        
        for video in videos:
            current_url = video.thumbnail_url
            filename = extract_filename_from_url(current_url)
            
            if not filename:
                print(f"Video {video.id}: Cannot extract filename from URL")
                error_count += 1
                continue
            
            # Determine new archive path
            new_path = determine_archive_path(video.id, filename)
            new_url = f"https://storage.googleapis.com/prompt-veo-videos/{new_path}"
            
            print(f"Video {video.id}: '{video.title}'")
            print(f"  Current: {current_url[:100]}...")
            print(f"  New: {new_url}")
            
            try:
                # Update the thumbnail URL
                query = text("""
                    UPDATE videos 
                    SET thumbnail_url = :new_url, updated_at = NOW()
                    WHERE id = :video_id
                """)
                
                result = session.execute(query, {
                    "video_id": video.id,
                    "new_url": new_url
                })
                session.commit()
                
                print(f"  ✅ Updated successfully")
                success_count += 1
                
            except Exception as e:
                print(f"  ❌ Error updating: {e}")
                session.rollback()
                error_count += 1
            
            print()
        
        print(f"UPDATE SUMMARY:")
        print(f"  ✅ Successful: {success_count}")
        print(f"  ❌ Errors: {error_count}")
        print(f"  📁 Total: {len(videos)}")
        
    except Exception as e:
        print(f"Error during process: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    print("FIX THUMBNAIL URLS")
    print("=" * 50)
    update_thumbnail_urls() 