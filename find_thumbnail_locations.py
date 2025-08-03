#!/usr/bin/env python3
"""
Find Thumbnail Locations
=======================

This script finds where thumbnails are actually located in the GCS bucket
and updates the URLs to point to the correct locations.
"""

import os
import sys
from google.cloud import storage
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
                status
            FROM videos 
            WHERE status = 'completed' AND thumbnail_url IS NOT NULL
            ORDER BY id
        """)
        
        result = session.execute(query)
        return result.fetchall()
    except Exception as e:
        print(f"Error fetching videos: {e}")
        return []

def find_thumbnail_in_gcs(bucket, filename):
    """Find a thumbnail file in GCS by searching through archive folders"""
    print(f"  Searching for: {filename}")
    
    # Search in archive folders
    blobs = bucket.list_blobs(prefix="archive/")
    
    for blob in blobs:
        if blob.name.endswith(filename):
            print(f"  ✅ Found at: {blob.name}")
            return blob.name
    
    print(f"  ❌ Not found in archive folders")
    return None

def update_thumbnail_urls_to_correct_locations():
    """Update thumbnail URLs to point to correct GCS locations"""
    
    # Initialize GCS client
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket("prompt-veo-videos")
    except Exception as e:
        print(f"Failed to connect to GCS: {e}")
        return
    
    # Connect to database
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
        not_found_count = 0
        
        for video in videos:
            print(f"Video {video.id}: '{video.title}'")
            
            # Extract filename from current URL
            current_url = video.thumbnail_url
            if current_url.startswith('https://storage.googleapis.com/prompt-veo-videos/'):
                current_path = current_url.replace('https://storage.googleapis.com/prompt-veo-videos/', '')
                filename = current_path.split('/')[-1]
            else:
                filename = current_url.split('/')[-1]
            
            # Find the actual location in GCS
            actual_path = find_thumbnail_in_gcs(bucket, filename)
            
            if actual_path:
                # Update the URL to point to the correct location
                new_url = f"https://storage.googleapis.com/prompt-veo-videos/{actual_path}"
                
                try:
                    # Update the database
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
                    
                    print(f"  ✅ Updated URL to: {new_url}")
                    success_count += 1
                    
                except Exception as e:
                    print(f"  ❌ Error updating database: {e}")
                    session.rollback()
                    error_count += 1
            else:
                not_found_count += 1
            
            print()
        
        print(f"UPDATE SUMMARY:")
        print(f"  ✅ Successful: {success_count}")
        print(f"  ❌ Errors: {error_count}")
        print(f"  📁 Not found: {not_found_count}")
        print(f"  📊 Total: {len(videos)}")
        
    except Exception as e:
        print(f"Error during process: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    print("FIND THUMBNAIL LOCATIONS")
    print("=" * 50)
    update_thumbnail_urls_to_correct_locations() 