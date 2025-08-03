#!/usr/bin/env python3
"""
Check Fixed Video
================

This script checks the fixed video ID 5 with its new slug.
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

def check_video_5(session):
    """Check video ID 5 details"""
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
                public,
                views,
                created_at,
                updated_at
            FROM videos 
            WHERE id = 5
        """)
        
        result = session.execute(query)
        video = result.fetchone()
        
        if video:
            print(f"\n{'='*80}")
            print(f"📹 FIXED VIDEO ID 5 DETAILS")
            print(f"{'='*80}")
            
            print(f"📋 Title: {video.title}")
            print(f"✍️  Prompt: {video.prompt}")
            print(f"🔗 Slug: {video.slug}")
            print(f"🌐 Public: {'✅ Yes' if video.public else '❌ No'}")
            print(f"📊 Status: {video.status}")
            print(f"👀 Views: {video.views}")
            print(f"📅 Created: {video.created_at}")
            print(f"📅 Updated: {video.updated_at}")
            
            print(f"\n🎬 GCS URL:")
            if video.gcs_url:
                print(f"   {video.gcs_url}")
                if 'archive' in video.gcs_url:
                    print(f"   ✅ Now in archive folder")
                else:
                    print(f"   ❌ Still not in archive folder")
            else:
                print(f"   ❌ NO GCS URL")
            
            print(f"\n🖼️  Thumbnail URL:")
            if video.thumbnail_url:
                print(f"   {video.thumbnail_url[:100]}...")
                if 'thumbnails' in video.thumbnail_url:
                    print(f"   ✅ In thumbnails folder")
                else:
                    print(f"   ❌ NOT in thumbnails folder")
            else:
                print(f"   ❌ NO THUMBNAIL URL")
            
            # Check new frontend URL
            print(f"\n🌐 NEW FRONTEND URL:")
            if video.slug:
                new_url = f"https://prompt-videos.com/watch/{video.id}-{video.slug}"
                print(f"   {new_url}")
                
                # Check if it should work
                if video.status == 'completed' and (video.public or video.user_id):
                    print(f"   ✅ Should be accessible on frontend")
                else:
                    print(f"   ❌ May not be accessible on frontend")
            else:
                print(f"   ❌ No slug available")
            
            # Check old URL
            print(f"\n🔗 OLD URL (should not work):")
            old_url = f"https://prompt-videos.com/watch/5-temp-abstract-geometric-patterns-forming-and-dissolving"
            print(f"   {old_url}")
            print(f"   ❌ Should return 404 (slug was changed)")
            
        else:
            print(f"❌ Video ID 5 not found")
            
    except Exception as e:
        print(f"❌ Error checking video: {e}")

def main():
    """Main check process"""
    print("🔍 CHECK FIXED VIDEO ID 5")
    print("=" * 50)
    
    # Connect to database
    engine, session = connect_to_database()
    if not engine or not session:
        return
    
    try:
        # Check video 5
        check_video_5(session)
        
    except Exception as e:
        print(f"❌ Error during check: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    main() 