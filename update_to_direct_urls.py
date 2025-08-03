#!/usr/bin/env python3
"""
Update to Direct URLs
====================

This script updates thumbnail URLs to use direct URLs instead of signed URLs.
Run this AFTER configuring public access to the GCS bucket.
"""

import os
import sys
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
    
    # Handle signed URLs (remove query parameters)
    if '?' in url:
        url = url.split('?')[0]
        if url.startswith('https://storage.googleapis.com/prompt-veo-videos/'):
            return url.replace('https://storage.googleapis.com/prompt-veo-videos/', '')
    
    return url

def update_to_direct_urls():
    """Update thumbnail URLs to use direct URLs"""
    
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
        
        for video in videos:
            gcs_path = extract_gcs_path_from_url(video.thumbnail_url)
            
            if not gcs_path:
                print(f"Video {video.id}: Cannot extract GCS path from URL")
                error_count += 1
                continue
            
            # Create direct URL
            direct_url = f"https://storage.googleapis.com/prompt-veo-videos/{gcs_path}"
            
            print(f"Video {video.id}: '{video.title}'")
            print(f"  Path: {gcs_path}")
            print(f"  Direct URL: {direct_url}")
            
            try:
                # Update the database with the direct URL
                query = text("""
                    UPDATE videos 
                    SET thumbnail_url = :new_url, updated_at = NOW()
                    WHERE id = :video_id
                """)
                
                result = session.execute(query, {
                    "video_id": video.id,
                    "new_url": direct_url
                })
                session.commit()
                
                print(f"  ✅ Updated to direct URL")
                success_count += 1
                
            except Exception as e:
                print(f"  ❌ Error updating: {e}")
                session.rollback()
                error_count += 1
            
            print()
        
        print(f"UPDATE SUMMARY:")
        print(f"  ✅ Successful: {success_count}")
        print(f"  ❌ Errors: {error_count}")
        print(f"  📊 Total: {len(videos)}")
        
        if success_count > 0:
            print(f"\n✅ {success_count} thumbnails now use direct URLs!")
            print("The thumbnails should now be visible on your website.")
            print()
            print("⚠️  IMPORTANT: Make sure you've configured public access to the GCS bucket!")
            print("If you haven't done this yet, follow the instructions in configure_public_access.md")
        
    except Exception as e:
        print(f"Error during process: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    print("UPDATE TO DIRECT URLS")
    print("=" * 50)
    print("⚠️  WARNING: This script assumes you've configured public access to the GCS bucket!")
    print("If you haven't done this yet, please follow the instructions in configure_public_access.md")
    print()
    
    response = input("Have you configured public access to the GCS bucket? (y/N): ")
    if response.lower() in ['y', 'yes']:
        update_to_direct_urls()
    else:
        print("Please configure public access first, then run this script again.")
        print("See configure_public_access.md for instructions.") 