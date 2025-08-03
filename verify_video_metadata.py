#!/usr/bin/env python3
"""
Video Metadata Verification Script
==================================

This script helps verify that videos in the database have correct metadata:
- Title
- Prompt  
- Thumbnail URL
- GCS Archive URL

It will show you each video's details so you can verify they match what's expected.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import requests
from urllib.parse import urlparse

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

def get_videos_for_verification(session):
    """Get videos that should be displayed on index/dashboard pages"""
    try:
        # Get completed videos that are public or have users
        query = text("""
            SELECT 
                v.id,
                v.title,
                v.prompt,
                v.thumbnail_url,
                v.gcs_url,
                v.gcs_signed_url,
                v.public,
                v.status,
                v.created_at,
                u.email as user_email,
                v.slug
            FROM videos v
            LEFT JOIN users u ON v.user_id = u.id
            WHERE v.status = 'completed'
            ORDER BY v.created_at DESC
            LIMIT 50
        """)
        
        result = session.execute(query)
        return result.fetchall()
    except Exception as e:
        print(f"❌ Error fetching videos: {e}")
        return []

def verify_gcs_url(url):
    """Check if GCS URL is accessible"""
    if not url:
        return False, "No URL provided"
    
    try:
        # For signed URLs, we can check if they're accessible
        if 'googleapis.com' in url and 'signature=' in url:
            response = requests.head(url, timeout=5)
            return response.status_code == 200, f"Status: {response.status_code}"
        else:
            # For unsigned URLs, just check format
            parsed = urlparse(url)
            return 'gs://' in url or 'googleapis.com' in url, "URL format looks correct"
    except Exception as e:
        return False, f"Error checking URL: {e}"

def verify_thumbnail_url(url):
    """Check if thumbnail URL is accessible"""
    if not url:
        return False, "No thumbnail URL"
    
    try:
        response = requests.head(url, timeout=5)
        return response.status_code == 200, f"Status: {response.status_code}"
    except Exception as e:
        return False, f"Error checking thumbnail: {e}"

def display_video_details(video, index):
    """Display detailed information about a video"""
    print(f"\n{'='*80}")
    print(f"📹 VIDEO #{index}: ID {video.id}")
    print(f"{'='*80}")
    
    # Basic info
    print(f"📋 Title: {video.title or 'NO TITLE'}")
    print(f"✍️  Prompt: {video.prompt[:100]}{'...' if len(video.prompt or '') > 100 else ''}")
    print(f"👤 User: {video.user_email or 'NO USER'}")
    print(f"🔗 Slug: {video.slug or 'NO SLUG'}")
    print(f"🌐 Public: {'✅ Yes' if video.public else '❌ No'}")
    print(f"📊 Status: {video.status}")
    print(f"📅 Created: {video.created_at}")
    
    # GCS URL verification
    print(f"\n🎬 GCS URL:")
    if video.gcs_url:
        print(f"   Raw URL: {video.gcs_url}")
        gcs_accessible, gcs_status = verify_gcs_url(video.gcs_url)
        print(f"   Status: {'✅ Accessible' if gcs_accessible else '❌ Not accessible'} - {gcs_status}")
    else:
        print("   ❌ NO GCS URL")
    
    if video.gcs_signed_url:
        print(f"   Signed URL: {video.gcs_signed_url[:100]}...")
        signed_accessible, signed_status = verify_gcs_url(video.gcs_signed_url)
        print(f"   Status: {'✅ Accessible' if signed_accessible else '❌ Not accessible'} - {signed_status}")
    else:
        print("   ❌ NO SIGNED URL")
    
    # Thumbnail verification
    print(f"\n🖼️  Thumbnail:")
    if video.thumbnail_url:
        print(f"   URL: {video.thumbnail_url}")
        thumb_accessible, thumb_status = verify_thumbnail_url(video.thumbnail_url)
        print(f"   Status: {'✅ Accessible' if thumb_accessible else '❌ Not accessible'} - {thumb_status}")
    else:
        print("   ❌ NO THUMBNAIL")
    
    # Archive folder check
    if video.gcs_url and 'archive' in video.gcs_url:
        print(f"   📁 Archive folder detected: ✅")
    elif video.gcs_url:
        print(f"   📁 Archive folder: ❌ (not in archive folder)")
    else:
        print(f"   📁 Archive folder: ❌ (no GCS URL)")

def main():
    """Main verification process"""
    print("🔍 VIDEO METADATA VERIFICATION")
    print("=" * 50)
    
    # Connect to database
    engine, session = connect_to_database()
    if not engine or not session:
        return
    
    try:
        # Get videos
        videos = get_videos_for_verification(session)
        if not videos:
            print("❌ No videos found in database")
            return
        
        print(f"📊 Found {len(videos)} videos to verify")
        
        # Display each video
        for i, video in enumerate(videos, 1):
            display_video_details(video, i)
            
            # Ask user if they want to continue
            if i < len(videos):
                response = input(f"\nPress Enter to continue to next video, or 'q' to quit: ")
                if response.lower() == 'q':
                    break
        
        print(f"\n✅ Verification complete! Checked {min(i, len(videos))} videos.")
        
        # Summary statistics
        print(f"\n📈 SUMMARY:")
        public_videos = sum(1 for v in videos if v.public)
        archive_videos = sum(1 for v in videos if v.gcs_url and 'archive' in v.gcs_url)
        thumbnails = sum(1 for v in videos if v.thumbnail_url)
        
        print(f"   Public videos: {public_videos}/{len(videos)}")
        print(f"   Archive folder videos: {archive_videos}/{len(videos)}")
        print(f"   Videos with thumbnails: {thumbnails}/{len(videos)}")
        
    except Exception as e:
        print(f"❌ Error during verification: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    main() 