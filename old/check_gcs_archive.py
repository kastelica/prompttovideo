#!/usr/bin/env python3
"""
Check GCS Archive Structure
==========================

This script checks if videos are properly stored in the archive folder and verifies GCS structure.
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
        print(f"❌ Failed to connect to database: {e}")
        return None, None

def get_videos_gcs_info(session):
    """Get GCS URL information for all videos"""
    try:
        query = text("""
            SELECT 
                id,
                title,
                gcs_url,
                gcs_signed_url,
                thumbnail_url,
                status,
                public
            FROM videos 
            WHERE status = 'completed'
            ORDER BY id
        """)
        
        result = session.execute(query)
        return result.fetchall()
    except Exception as e:
        print(f"❌ Error fetching videos: {e}")
        return []

def analyze_gcs_structure(videos):
    """Analyze GCS URL structure"""
    print(f"\n🔍 GCS STRUCTURE ANALYSIS")
    print("=" * 50)
    
    # Count different patterns
    patterns = {
        'archive': 0,
        'videos': 0,
        'thumbnails': 0,
        'other': 0
    }
    
    archive_videos = []
    non_archive_videos = []
    
    for video in videos:
        if video.gcs_url:
            if 'archive' in video.gcs_url:
                patterns['archive'] += 1
                archive_videos.append(video)
            elif 'videos' in video.gcs_url:
                patterns['videos'] += 1
                non_archive_videos.append(video)
            else:
                patterns['other'] += 1
        
        if video.thumbnail_url and 'thumbnails' in video.thumbnail_url:
            patterns['thumbnails'] += 1
    
    print(f"📊 GCS URL Patterns:")
    print(f"   Archive folder: {patterns['archive']} videos")
    print(f"   Videos folder: {patterns['videos']} videos")
    print(f"   Thumbnails folder: {patterns['thumbnails']} videos")
    print(f"   Other patterns: {patterns['other']} videos")
    
    if non_archive_videos:
        print(f"\n📂 Videos NOT in archive folder:")
        print("-" * 40)
        for video in non_archive_videos[:10]:  # Show first 10
            print(f"   ID {video.id}: {video.title or 'NO TITLE'}")
            print(f"      GCS: {video.gcs_url}")
            print()
        
        if len(non_archive_videos) > 10:
            print(f"   ... and {len(non_archive_videos) - 10} more")
    
    if archive_videos:
        print(f"\n📁 Videos IN archive folder:")
        print("-" * 40)
        for video in archive_videos[:5]:  # Show first 5
            print(f"   ID {video.id}: {video.title or 'NO TITLE'}")
            print(f"      GCS: {video.gcs_url}")
            print()
        
        if len(archive_videos) > 5:
            print(f"   ... and {len(archive_videos) - 5} more")
    
    return non_archive_videos, archive_videos

def check_specific_video(video_id, session):
    """Check a specific video's GCS structure"""
    try:
        query = text("""
            SELECT 
                id,
                title,
                prompt,
                gcs_url,
                gcs_signed_url,
                thumbnail_url,
                status,
                public,
                slug
            FROM videos 
            WHERE id = :video_id
        """)
        
        result = session.execute(query, {"video_id": video_id})
        video = result.fetchone()
        
        if video:
            print(f"\n🔍 DETAILED CHECK FOR VIDEO ID {video_id}")
            print("=" * 60)
            print(f"📋 Title: {video.title or 'NO TITLE'}")
            print(f"✍️  Prompt: {video.prompt or 'NO PROMPT'}")
            print(f"🔗 Slug: {video.slug or 'NO SLUG'}")
            print(f"🌐 Public: {'✅ Yes' if video.public else '❌ No'}")
            print(f"📊 Status: {video.status}")
            
            print(f"\n🎬 GCS URL:")
            if video.gcs_url:
                print(f"   {video.gcs_url}")
                if 'archive' in video.gcs_url:
                    print(f"   ✅ In archive folder")
                else:
                    print(f"   ❌ NOT in archive folder")
            else:
                print(f"   ❌ NO GCS URL")
            
            print(f"\n🖼️  Thumbnail URL:")
            if video.thumbnail_url:
                print(f"   {video.thumbnail_url}")
                if 'thumbnails' in video.thumbnail_url:
                    print(f"   ✅ In thumbnails folder")
                else:
                    print(f"   ❌ NOT in thumbnails folder")
            else:
                print(f"   ❌ NO THUMBNAIL URL")
            
            # Check for title/slug mismatch
            if video.title and video.slug:
                title_words = set(video.title.lower().split())
                slug_words = set(video.slug.lower().replace('-', ' ').split())
                common_words = title_words.intersection(slug_words)
                
                if len(common_words) == 0:
                    print(f"\n⚠️  TITLE/SLUG MISMATCH:")
                    print(f"   Title: '{video.title}'")
                    print(f"   Slug: '{video.slug}'")
                    print(f"   No common words found!")
                else:
                    print(f"\n✅ Title and slug have {len(common_words)} common words")
        else:
            print(f"❌ Video ID {video_id} not found")
            
    except Exception as e:
        print(f"❌ Error checking video: {e}")

def main():
    """Main analysis process"""
    print("🔍 GCS ARCHIVE STRUCTURE CHECK")
    print("=" * 50)
    
    # Connect to database
    engine, session = connect_to_database()
    if not engine or not session:
        return
    
    try:
        # Get all videos
        videos = get_videos_gcs_info(session)
        if not videos:
            print("❌ No videos found")
            return
        
        print(f"📊 Found {len(videos)} completed videos")
        
        # Analyze GCS structure
        non_archive, archive = analyze_gcs_structure(videos)
        
        # Check specific video (ID 5)
        check_specific_video(5, session)
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        print("-" * 40)
        
        if non_archive:
            print(f"   • Move {len(non_archive)} videos to archive folder")
            print(f"   • Update GCS URLs to point to archive/ subfolder")
        
        print(f"   • Fix title/slug mismatches for better SEO")
        print(f"   • Ensure all videos have proper thumbnails")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    main() 