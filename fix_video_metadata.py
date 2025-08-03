#!/usr/bin/env python3
"""
Fix Video Metadata Issues
========================

This script fixes common video metadata issues:
1. Title/slug mismatches
2. Moving videos to archive folder
3. Updating GCS URLs
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
        print(f"❌ Failed to connect to database: {e}")
        return None, None

def generate_slug_from_title(title):
    """Generate a proper slug from title"""
    if not title:
        return None
    
    # Convert to lowercase and replace spaces with hyphens
    slug = title.lower()
    # Remove special characters except hyphens
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    # Replace multiple spaces/hyphens with single hyphen
    slug = re.sub(r'[\s-]+', '-', slug)
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    
    return slug

def get_videos_with_issues(session):
    """Get videos that need fixing"""
    try:
        query = text("""
            SELECT 
                id,
                title,
                prompt,
                slug,
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

def analyze_title_slug_mismatches(videos):
    """Analyze title/slug mismatches"""
    mismatches = []
    
    for video in videos:
        if video.title and video.slug:
            # Generate expected slug from title
            expected_slug = generate_slug_from_title(video.title)
            
            # Check if current slug matches expected
            if expected_slug and video.slug != expected_slug:
                # Check for common words
                title_words = set(video.title.lower().split())
                slug_words = set(video.slug.lower().replace('-', ' ').split())
                common_words = title_words.intersection(slug_words)
                
                mismatches.append({
                    'video': video,
                    'expected_slug': expected_slug,
                    'common_words': len(common_words)
                })
    
    return mismatches

def fix_video_slug(session, video_id, new_slug):
    """Fix a video's slug"""
    try:
        query = text("""
            UPDATE videos 
            SET slug = :new_slug, updated_at = NOW()
            WHERE id = :video_id
        """)
        
        result = session.execute(query, {
            "video_id": video_id,
            "new_slug": new_slug
        })
        session.commit()
        
        return result.rowcount > 0
    except Exception as e:
        print(f"❌ Error fixing slug for video {video_id}: {e}")
        session.rollback()
        return False

def update_gcs_url_to_archive(session, video_id, new_gcs_url):
    """Update GCS URL to point to archive folder"""
    try:
        query = text("""
            UPDATE videos 
            SET gcs_url = :new_gcs_url, updated_at = NOW()
            WHERE id = :video_id
        """)
        
        result = session.execute(query, {
            "video_id": video_id,
            "new_gcs_url": new_gcs_url
        })
        session.commit()
        
        return result.rowcount > 0
    except Exception as e:
        print(f"❌ Error updating GCS URL for video {video_id}: {e}")
        session.rollback()
        return False

def main():
    """Main fix process"""
    print("🔧 FIX VIDEO METADATA ISSUES")
    print("=" * 50)
    
    # Connect to database
    engine, session = connect_to_database()
    if not engine or not session:
        return
    
    try:
        # Get all videos
        videos = get_videos_with_issues(session)
        if not videos:
            print("❌ No videos found")
            return
        
        print(f"📊 Found {len(videos)} completed videos to analyze")
        
        # Analyze title/slug mismatches
        mismatches = analyze_title_slug_mismatches(videos)
        
        print(f"\n🔍 TITLE/SLUG MISMATCHES:")
        print("-" * 40)
        
        if mismatches:
            print(f"Found {len(mismatches)} videos with title/slug mismatches:")
            print()
            
            for i, mismatch in enumerate(mismatches, 1):
                video = mismatch['video']
                expected_slug = mismatch['expected_slug']
                common_words = mismatch['common_words']
                
                print(f"{i}. ID {video.id}: '{video.title}'")
                print(f"   Current slug: {video.slug}")
                print(f"   Expected slug: {expected_slug}")
                print(f"   Common words: {common_words}")
                print()
            
            # Ask user if they want to fix
            response = input("Do you want to fix these slug mismatches? (y/n): ")
            
            if response.lower() == 'y':
                print(f"\n🔧 Fixing slug mismatches...")
                fixed_count = 0
                
                for mismatch in mismatches:
                    video = mismatch['video']
                    expected_slug = mismatch['expected_slug']
                    
                    if fix_video_slug(session, video.id, expected_slug):
                        print(f"   ✅ Fixed video {video.id}: '{video.slug}' → '{expected_slug}'")
                        fixed_count += 1
                    else:
                        print(f"   ❌ Failed to fix video {video.id}")
                
                print(f"\n✅ Fixed {fixed_count} slug mismatches")
        else:
            print("✅ No title/slug mismatches found")
        
        # Analyze GCS archive structure
        print(f"\n🔍 GCS ARCHIVE STRUCTURE:")
        print("-" * 40)
        
        non_archive_videos = [v for v in videos if v.gcs_url and 'archive' not in v.gcs_url]
        
        if non_archive_videos:
            print(f"Found {len(non_archive_videos)} videos not in archive folder:")
            print()
            
            for i, video in enumerate(non_archive_videos[:5], 1):
                print(f"{i}. ID {video.id}: {video.title}")
                print(f"   Current: {video.gcs_url}")
                print()
            
            if len(non_archive_videos) > 5:
                print(f"... and {len(non_archive_videos) - 5} more")
            
            # Ask user if they want to fix
            response = input("Do you want to update GCS URLs to archive folder? (y/n): ")
            
            if response.lower() == 'y':
                print(f"\n🔧 Updating GCS URLs to archive folder...")
                updated_count = 0
                
                for video in non_archive_videos:
                    if video.gcs_url:
                        # Convert to archive path
                        new_gcs_url = video.gcs_url.replace('/videos/', '/archive/videos/')
                        
                        if update_gcs_url_to_archive(session, video.id, new_gcs_url):
                            print(f"   ✅ Updated video {video.id}: {video.gcs_url} → {new_gcs_url}")
                            updated_count += 1
                        else:
                            print(f"   ❌ Failed to update video {video.id}")
                
                print(f"\n✅ Updated {updated_count} GCS URLs")
        else:
            print("✅ All videos are already in archive folder")
        
        # Summary
        print(f"\n📈 SUMMARY:")
        print("-" * 40)
        print(f"   Videos analyzed: {len(videos)}")
        print(f"   Slug mismatches found: {len(mismatches)}")
        print(f"   Videos not in archive: {len(non_archive_videos)}")
        
    except Exception as e:
        print(f"❌ Error during fix process: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    main() 