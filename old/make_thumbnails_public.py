#!/usr/bin/env python3
"""
Make Thumbnails Public
=====================

This script makes thumbnail files in GCS publicly readable so they can be
accessed without authentication.
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

def extract_gcs_path_from_url(url):
    """Extract GCS path from URL"""
    if not url:
        return None
    
    # Handle https:// URLs
    if url.startswith('https://storage.googleapis.com/prompt-veo-videos/'):
        return url.replace('https://storage.googleapis.com/prompt-veo-videos/', '')
    
    # Handle gs:// URLs
    if url.startswith('gs://prompt-veo-videos/'):
        return url.replace('gs://prompt-veo-videos/', '')
    
    return url

def make_thumbnails_public():
    """Make thumbnail files publicly readable"""
    
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
            gcs_path = extract_gcs_path_from_url(video.thumbnail_url)
            
            if not gcs_path:
                print(f"Video {video.id}: Cannot extract GCS path from URL")
                error_count += 1
                continue
            
            print(f"Video {video.id}: '{video.title}'")
            print(f"  Path: {gcs_path}")
            
            try:
                # Get the blob
                blob = bucket.blob(gcs_path)
                
                if not blob.exists():
                    print(f"  ❌ File not found in GCS")
                    not_found_count += 1
                    continue
                
                # Make the blob publicly readable
                blob.make_public()
                
                print(f"  ✅ Made public successfully")
                print(f"  📎 Public URL: {blob.public_url}")
                success_count += 1
                
            except Exception as e:
                print(f"  ❌ Error making public: {e}")
                error_count += 1
            
            print()
        
        print(f"PUBLIC ACCESS SUMMARY:")
        print(f"  ✅ Successful: {success_count}")
        print(f"  ❌ Errors: {error_count}")
        print(f"  📁 Not found: {not_found_count}")
        print(f"  📊 Total: {len(videos)}")
        
        if success_count > 0:
            print(f"\n✅ {success_count} thumbnails are now publicly accessible!")
            print("The thumbnails should now be visible on your website.")
        
    except Exception as e:
        print(f"Error during process: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    print("MAKE THUMBNAILS PUBLIC")
    print("=" * 50)
    make_thumbnails_public() 