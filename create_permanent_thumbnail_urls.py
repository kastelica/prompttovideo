#!/usr/bin/env python3
"""
Create Permanent Thumbnail URLs
==============================

This script creates signed URLs with very long expiration times (10 years)
for thumbnails so they remain accessible permanently.
"""

import os
import sys
from datetime import datetime, timedelta
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

def create_permanent_thumbnail_urls():
    """Create signed URLs with very long expiration for thumbnails"""
    
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
        
        # Set expiration to 10 years from now
        expiration = datetime.now() + timedelta(days=3650)  # 10 years
        
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
                
                # Generate signed URL with 10-year expiration
                signed_url = blob.generate_signed_url(
                    version="v4",
                    expiration=expiration,
                    method="GET"
                )
                
                # Update the database with the new signed URL
                query = text("""
                    UPDATE videos 
                    SET thumbnail_url = :new_url, updated_at = NOW()
                    WHERE id = :video_id
                """)
                
                result = session.execute(query, {
                    "video_id": video.id,
                    "new_url": signed_url
                })
                session.commit()
                
                print(f"  ✅ Created permanent URL (expires: {expiration.strftime('%Y-%m-%d')})")
                print(f"  📎 URL: {signed_url[:100]}...")
                success_count += 1
                
            except Exception as e:
                print(f"  ❌ Error creating signed URL: {e}")
                session.rollback()
                error_count += 1
            
            print()
        
        print(f"PERMANENT URL SUMMARY:")
        print(f"  ✅ Successful: {success_count}")
        print(f"  ❌ Errors: {error_count}")
        print(f"  📁 Not found: {not_found_count}")
        print(f"  📊 Total: {len(videos)}")
        
        if success_count > 0:
            print(f"\n✅ {success_count} thumbnails now have permanent URLs!")
            print(f"These URLs will be valid until {expiration.strftime('%Y-%m-%d')}")
            print("The thumbnails should now be visible on your website.")
        
    except Exception as e:
        print(f"Error during process: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    print("CREATE PERMANENT THUMBNAIL URLS")
    print("=" * 50)
    create_permanent_thumbnail_urls() 