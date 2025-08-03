#!/usr/bin/env python3
"""
Test Thumbnails Display
======================

This script tests if thumbnail URLs are working and provides sample URLs
for manual testing in the browser.
"""

import os
import sys
import requests
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

def get_sample_videos(session):
    """Get sample videos for testing"""
    try:
        query = text("""
            SELECT 
                id,
                title,
                prompt,
                thumbnail_url,
                status,
                public
            FROM videos 
            WHERE status = 'completed' AND thumbnail_url IS NOT NULL
            ORDER BY id
            LIMIT 5
        """)
        
        result = session.execute(query)
        return result.fetchall()
    except Exception as e:
        print(f"Error fetching videos: {e}")
        return []

def test_thumbnail_url(url):
    """Test if a thumbnail URL is accessible"""
    try:
        response = requests.head(url, timeout=10)
        return response.status_code == 200
    except Exception as e:
        return False

def main():
    """Test thumbnail URLs"""
    print("TESTING THUMBNAIL DISPLAY")
    print("=" * 50)
    
    # Connect to database
    engine, session = connect_to_database()
    if not engine or not session:
        return
    
    try:
        # Get sample videos
        videos = get_sample_videos(session)
        if not videos:
            print("No videos found with thumbnails")
            return
        
        print(f"Testing {len(videos)} sample videos:")
        print()
        
        working_count = 0
        broken_count = 0
        
        for video in videos:
            print(f"Video {video.id}: '{video.title or video.prompt[:50]}'")
            print(f"  Thumbnail URL: {video.thumbnail_url}")
            
            # Test URL accessibility
            is_working = test_thumbnail_url(video.thumbnail_url)
            
            if is_working:
                print(f"  ✅ Status: WORKING (200 OK)")
                working_count += 1
            else:
                print(f"  ❌ Status: BROKEN (not accessible)")
                broken_count += 1
            
            print()
        
        print(f"SUMMARY:")
        print(f"  ✅ Working thumbnails: {working_count}")
        print(f"  ❌ Broken thumbnails: {broken_count}")
        print(f"  📊 Total tested: {len(videos)}")
        print()
        
        if working_count > 0:
            print("🎉 Thumbnails are working! The issue might be:")
            print("   1. Browser caching - try hard refresh (Ctrl+F5)")
            print("   2. CSS/styling issues in the templates")
            print("   3. JavaScript errors preventing display")
            print()
            print("Try opening these URLs directly in your browser:")
            for video in videos:
                if test_thumbnail_url(video.thumbnail_url):
                    print(f"   {video.thumbnail_url}")
        else:
            print("❌ All thumbnails are broken. Check the GCS bucket permissions.")
        
    except Exception as e:
        print(f"Error during testing: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    main() 