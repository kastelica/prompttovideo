#!/usr/bin/env python3
"""
Quick Video Metadata Check
==========================

This script provides a quick overview of all video metadata without interactive prompts.
Useful for getting a fast summary of video status.
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

def get_all_videos(session):
    """Get all completed videos"""
    try:
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
        """)
        
        result = session.execute(query)
        return result.fetchall()
    except Exception as e:
        print(f"❌ Error fetching videos: {e}")
        return []

def check_url_accessibility(url):
    """Quick check if URL is accessible"""
    if not url:
        return False
    
    try:
        if 'googleapis.com' in url and 'signature=' in url:
            response = requests.head(url, timeout=3)
            return response.status_code == 200
        else:
            return 'gs://' in url or 'googleapis.com' in url
    except:
        return False

def main():
    """Quick overview of all videos"""
    print("🔍 QUICK VIDEO METADATA CHECK")
    print("=" * 40)
    
    # Connect to database
    engine, session = connect_to_database()
    if not engine or not session:
        return
    
    try:
        # Get videos
        videos = get_all_videos(session)
        if not videos:
            print("❌ No videos found in database")
            return
        
        print(f"📊 Found {len(videos)} completed videos")
        print()
        
        # Statistics
        public_videos = sum(1 for v in videos if v.public)
        archive_videos = sum(1 for v in videos if v.gcs_url and 'archive' in v.gcs_url)
        thumbnails = sum(1 for v in videos if v.thumbnail_url)
        accessible_gcs = sum(1 for v in videos if v.gcs_url and check_url_accessibility(v.gcs_url))
        accessible_signed = sum(1 for v in videos if v.gcs_signed_url and check_url_accessibility(v.gcs_signed_url))
        accessible_thumbnails = sum(1 for v in videos if v.thumbnail_url and check_url_accessibility(v.thumbnail_url))
        
        print("📈 OVERALL STATISTICS:")
        print(f"   Public videos: {public_videos}/{len(videos)} ({public_videos/len(videos)*100:.1f}%)")
        print(f"   Archive folder videos: {archive_videos}/{len(videos)} ({archive_videos/len(videos)*100:.1f}%)")
        print(f"   Videos with thumbnails: {thumbnails}/{len(videos)} ({thumbnails/len(videos)*100:.1f}%)")
        print(f"   Accessible GCS URLs: {accessible_gcs}/{len(videos)} ({accessible_gcs/len(videos)*100:.1f}%)")
        print(f"   Accessible signed URLs: {accessible_signed}/{len(videos)} ({accessible_signed/len(videos)*100:.1f}%)")
        print(f"   Accessible thumbnails: {accessible_thumbnails}/{len(videos)} ({accessible_thumbnails/len(videos)*100:.1f}%)")
        
        print()
        print("🔍 DETAILED BREAKDOWN:")
        print("-" * 40)
        
        # Show first 10 videos in detail
        for i, video in enumerate(videos[:10], 1):
            print(f"{i:2d}. ID {video.id:3d} | {video.title or 'NO TITLE':<30} | {'✅' if video.public else '❌'} | {'📁' if video.gcs_url and 'archive' in video.gcs_url else '📂'} | {video.user_email or 'NO USER'}")
        
        if len(videos) > 10:
            print(f"... and {len(videos) - 10} more videos")
        
        print()
        print("❌ PROBLEMS FOUND:")
        print("-" * 40)
        
        # Find problems
        no_title = [v for v in videos if not v.title]
        no_gcs = [v for v in videos if not v.gcs_url]
        no_thumbnail = [v for v in videos if not v.thumbnail_url]
        not_archive = [v for v in videos if v.gcs_url and 'archive' not in v.gcs_url]
        not_public = [v for v in videos if not v.public]
        
        if no_title:
            print(f"   Videos without titles: {len(no_title)} (IDs: {[v.id for v in no_title[:5]]}{'...' if len(no_title) > 5 else ''})")
        if no_gcs:
            print(f"   Videos without GCS URLs: {len(no_gcs)} (IDs: {[v.id for v in no_gcs[:5]]}{'...' if len(no_gcs) > 5 else ''})")
        if no_thumbnail:
            print(f"   Videos without thumbnails: {len(no_thumbnail)} (IDs: {[v.id for v in no_thumbnail[:5]]}{'...' if len(no_thumbnail) > 5 else ''})")
        if not_archive:
            print(f"   Videos not in archive folder: {len(not_archive)} (IDs: {[v.id for v in not_archive[:5]]}{'...' if len(not_archive) > 5 else ''})")
        if not_public:
            print(f"   Private videos: {len(not_public)} (IDs: {[v.id for v in not_public[:5]]}{'...' if len(not_public) > 5 else ''})")
        
        if not any([no_title, no_gcs, no_thumbnail, not_archive, not_public]):
            print("   ✅ No major problems found!")
        
        print()
        print("💡 RECOMMENDATIONS:")
        print("-" * 40)
        
        if not_public:
            print(f"   • Make {len(not_public)} private videos public")
        if not_archive:
            print(f"   • Move {len(not_archive)} videos to archive folder")
        if no_title:
            print(f"   • Add titles to {len(no_title)} videos")
        if no_thumbnail:
            print(f"   • Generate thumbnails for {len(no_thumbnail)} videos")
        
        print("   • Run verify_video_metadata.py for detailed inspection")
        
    except Exception as e:
        print(f"❌ Error during check: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    main() 