#!/usr/bin/env python3
"""
Check Thumbnail URLs
===================

This script checks the current thumbnail URLs in the database and identifies
which ones need to be updated to point to the archive folder.
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

def analyze_thumbnail_urls(videos):
    """Analyze thumbnail URLs to see which need updating"""
    print("ANALYZING THUMBNAIL URLS")
    print("=" * 50)
    
    archive_thumbnails = []
    non_archive_thumbnails = []
    missing_thumbnails = []
    
    for video in videos:
        print(f"\nVideo ID {video.id}: '{video.title}'")
        print(f"  Thumbnail URL: {video.thumbnail_url}")
        
        if video.thumbnail_url:
            if 'archive' in video.thumbnail_url:
                archive_thumbnails.append(video)
                print(f"  Already in archive folder")
            else:
                non_archive_thumbnails.append(video)
                print(f"  NOT in archive folder")
        else:
            missing_thumbnails.append(video)
            print(f"  NO THUMBNAIL URL")
    
    return archive_thumbnails, non_archive_thumbnails, missing_thumbnails

def suggest_thumbnail_updates(non_archive_thumbnails):
    """Suggest how to update thumbnail URLs"""
    print(f"\nTHUMBNAIL UPDATE SUGGESTIONS")
    print("=" * 50)
    
    if not non_archive_thumbnails:
        print("All thumbnails are already in archive folder!")
        return
    
    print(f"Found {len(non_archive_thumbnails)} thumbnails that need updating:")
    print()
    
    for video in non_archive_thumbnails:
        current_url = video.thumbnail_url
        
        # Try to extract the filename from the current URL
        if 'thumbnails/' in current_url:
            # Extract the filename part
            parts = current_url.split('thumbnails/')
            if len(parts) > 1:
                filename = parts[1].split('?')[0]  # Remove query parameters
                new_url = f"https://storage.googleapis.com/prompt-veo-videos/thumbnails/{filename}"
                
                print(f"Video {video.id}: '{video.title}'")
                print(f"  Current: {current_url}")
                print(f"  Suggested: {new_url}")
                print()
        else:
            print(f"Video {video.id}: '{video.title}'")
            print(f"  Current: {current_url}")
            print(f"  Cannot determine new URL format")
            print()

def main():
    """Main process"""
    print("CHECK THUMBNAIL URLS")
    print("=" * 50)
    
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
        
        # Analyze thumbnail URLs
        archive_thumbnails, non_archive_thumbnails, missing_thumbnails = analyze_thumbnail_urls(videos)
        
        # Show summary
        print(f"\nSUMMARY:")
        print("-" * 30)
        print(f"Already in archive: {len(archive_thumbnails)}")
        print(f"Need updating: {len(non_archive_thumbnails)}")
        print(f"Missing thumbnails: {len(missing_thumbnails)}")
        
        # Suggest updates
        suggest_thumbnail_updates(non_archive_thumbnails)
        
        if non_archive_thumbnails:
            print(f"\nReady to update {len(non_archive_thumbnails)} thumbnail URLs!")
            print("You can manually update the thumbnail_url field in the database")
            print("or create a script to automate the updates.")
        else:
            print(f"\nAll thumbnails are properly configured!")
        
    except Exception as e:
        print(f"Error during process: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    main() 