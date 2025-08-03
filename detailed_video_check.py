#!/usr/bin/env python3
"""
Detailed Video Check
===================

This script performs a detailed check of all metadata for a specific video.
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

def get_detailed_video_info(session, video_id):
    """Get all metadata for a specific video"""
    try:
        query = text("""
            SELECT 
                v.*,
                u.email as user_email,
                u.username
            FROM videos v
            LEFT JOIN users u ON v.user_id = u.id
            WHERE v.id = :video_id
        """)
        
        result = session.execute(query, {"video_id": video_id})
        return result.fetchone()
    except Exception as e:
        print(f"❌ Error fetching video: {e}")
        return None

def display_all_metadata(video):
    """Display all metadata fields for a video"""
    if not video:
        print("❌ Video not found!")
        return
    
    print(f"\n{'='*80}")
    print(f"📹 COMPLETE METADATA FOR VIDEO ID {video.id}")
    print(f"{'='*80}")
    
    # Get all column names
    columns = video._fields if hasattr(video, '_fields') else [key for key in video._mapping.keys()]
    
    for column in columns:
        value = getattr(video, column) if hasattr(video, column) else video._mapping[column]
        if value is None:
            print(f"❌ {column}: NULL")
        elif value == "":
            print(f"⚠️  {column}: (empty string)")
        else:
            print(f"✅ {column}: {value}")
    
    # Special analysis
    print(f"\n🔍 ANALYSIS:")
    print("-" * 40)
    
    # Check for missing critical fields
    missing_fields = []
    if not video.gcs_url:
        missing_fields.append("gcs_url")
    if not video.gcs_signed_url:
        missing_fields.append("gcs_signed_url")
    if not video.thumbnail_url:
        missing_fields.append("thumbnail_url")
    if not video.title:
        missing_fields.append("title")
    if not video.prompt:
        missing_fields.append("prompt")
    
    if missing_fields:
        print(f"❌ Missing critical fields: {', '.join(missing_fields)}")
    else:
        print(f"✅ All critical fields present")
    
    # Check status
    if video.status != 'completed':
        print(f"⚠️  Status is '{video.status}', not 'completed'")
    else:
        print(f"✅ Status is 'completed'")
    
    # Check public status
    if not video.public:
        print(f"⚠️  Video is not public")
    else:
        print(f"✅ Video is public")
    
    # Check if video should be accessible
    if video.status == 'completed' and (video.public or video.user_id):
        print(f"✅ Should be accessible on frontend")
    else:
        print(f"❌ May not be accessible on frontend")
        if video.status != 'completed':
            print(f"   - Status is '{video.status}', not 'completed'")
        if not video.public and not video.user_id:
            print(f"   - Not public and no user_id")

def main():
    """Main check process"""
    print("🔍 DETAILED VIDEO METADATA CHECK")
    print("=" * 50)
    
    video_id = 5
    
    print(f"🔍 Checking video ID: {video_id}")
    
    # Connect to database
    engine, session = connect_to_database()
    if not engine or not session:
        return
    
    try:
        # Get detailed video info
        video = get_detailed_video_info(session, video_id)
        
        if video:
            display_all_metadata(video)
        else:
            print(f"❌ Video ID {video_id} not found")
            
            # Check what video IDs exist
            print(f"\n🔍 Checking what video IDs exist...")
            id_query = text("""
                SELECT id, slug, title, status 
                FROM videos 
                ORDER BY id
                LIMIT 20
            """)
            
            id_result = session.execute(id_query)
            existing_videos = id_result.fetchall()
            
            if existing_videos:
                print(f"📋 Existing video IDs:")
                for v in existing_videos:
                    print(f"   ID {v.id}: {v.slug} | {v.title or 'NO TITLE'} | {v.status}")
            else:
                print(f"   No videos found in database")
        
    except Exception as e:
        print(f"❌ Error during check: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    main() 