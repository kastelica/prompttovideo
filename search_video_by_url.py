#!/usr/bin/env python3
"""
Search Video by URL
==================

This script searches for a specific video by its URL slug and displays all metadata.
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

def search_video_by_slug(session, slug):
    """Search for video by slug"""
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
                v.updated_at,
                v.user_id,
                v.slug,
                v.views,
                v.duration,
                u.email as user_email,
                u.username
            FROM videos v
            LEFT JOIN users u ON v.user_id = u.id
            WHERE v.slug = :slug
        """)
        
        result = session.execute(query, {"slug": slug})
        return result.fetchone()
    except Exception as e:
        print(f"❌ Error searching for video: {e}")
        return None

def check_url_accessibility(url):
    """Check if URL is accessible"""
    if not url:
        return False, "No URL provided"
    
    try:
        if 'googleapis.com' in url and 'signature=' in url:
            response = requests.head(url, timeout=5)
            return response.status_code == 200, f"Status: {response.status_code}"
        else:
            # For unsigned URLs, just check format
            parsed = urlparse(url)
            return 'gs://' in url or 'googleapis.com' in url, "URL format looks correct"
    except Exception as e:
        return False, f"Error checking URL: {e}"

def display_video_details(video):
    """Display detailed information about a video"""
    if not video:
        print("❌ Video not found!")
        return
    
    print(f"\n{'='*80}")
    print(f"📹 VIDEO DETAILS: ID {video.id}")
    print(f"{'='*80}")
    
    # Basic info
    print(f"📋 Title: {video.title or 'NO TITLE'}")
    print(f"✍️  Prompt: {video.prompt or 'NO PROMPT'}")
    print(f"👤 User: {video.user_email or 'NO USER'} (ID: {video.user_id or 'N/A'})")
    print(f"🔗 Slug: {video.slug or 'NO SLUG'}")
    print(f"🌐 Public: {'✅ Yes' if video.public else '❌ No'}")
    print(f"📊 Status: {video.status}")
    print(f"👀 Views: {video.views or 0}")
    print(f"⏱️  Duration: {video.duration or 'N/A'} seconds")
    print(f"📅 Created: {video.created_at}")
    print(f"📅 Updated: {video.updated_at}")
    
    # GCS URL verification
    print(f"\n🎬 GCS URL:")
    if video.gcs_url:
        print(f"   Raw URL: {video.gcs_url}")
        gcs_accessible, gcs_status = check_url_accessibility(video.gcs_url)
        print(f"   Status: {'✅ Accessible' if gcs_accessible else '❌ Not accessible'} - {gcs_status}")
    else:
        print("   ❌ NO GCS URL")
    
    if video.gcs_signed_url:
        print(f"   Signed URL: {video.gcs_signed_url[:100]}...")
        signed_accessible, signed_status = check_url_accessibility(video.gcs_signed_url)
        print(f"   Status: {'✅ Accessible' if signed_accessible else '❌ Not accessible'} - {signed_status}")
    else:
        print("   ❌ NO SIGNED URL")
    
    # Thumbnail verification
    print(f"\n🖼️  Thumbnail:")
    if video.thumbnail_url:
        print(f"   URL: {video.thumbnail_url}")
        thumb_accessible, thumb_status = check_url_accessibility(video.thumbnail_url)
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
    
    # Frontend URL
    print(f"\n🌐 Frontend URL:")
    if video.slug:
        frontend_url = f"https://prompt-videos.com/watch/{video.id}-{video.slug}"
        print(f"   {frontend_url}")
        
        # Check if frontend URL would work
        if video.status == 'completed' and (video.public or video.user_id):
            print(f"   ✅ Should be accessible on frontend")
        else:
            print(f"   ❌ May not be accessible on frontend")
            if video.status != 'completed':
                print(f"      - Status is '{video.status}', not 'completed'")
            if not video.public and not video.user_id:
                print(f"      - Not public and no user_id")
    else:
        print("   ❌ No slug available")

def main():
    """Main search process"""
    print("🔍 SEARCH VIDEO BY URL")
    print("=" * 50)
    
    # Extract slug from URL
    url = "https://prompt-videos.com/watch/5-temp-abstract-geometric-patterns-forming-and-dissolving"
    slug = "temp-abstract-geometric-patterns-forming-and-dissolving"
    
    print(f"🔍 Searching for slug: {slug}")
    print(f"🔗 From URL: {url}")
    
    # Connect to database
    engine, session = connect_to_database()
    if not engine or not session:
        return
    
    try:
        # Search for video
        video = search_video_by_slug(session, slug)
        
        if video:
            display_video_details(video)
            
            # Additional checks
            print(f"\n🔍 ADDITIONAL CHECKS:")
            print("-" * 40)
            
            # Check if there are other videos with similar slugs
            similar_query = text("""
                SELECT id, slug, title, status, public 
                FROM videos 
                WHERE slug LIKE :pattern
                ORDER BY id
            """)
            
            similar_result = session.execute(similar_query, {"pattern": f"%{slug.split('-')[0]}%"})
            similar_videos = similar_result.fetchall()
            
            if similar_videos:
                print(f"📋 Similar videos found:")
                for v in similar_videos:
                    print(f"   ID {v.id}: {v.slug} | {v.title or 'NO TITLE'} | {v.status} | {'✅' if v.public else '❌'}")
            
            # Check if video ID 5 exists
            id_query = text("""
                SELECT id, slug, title, status, public 
                FROM videos 
                WHERE id = 5
            """)
            
            id_result = session.execute(id_query)
            id_video = id_result.fetchone()
            
            if id_video:
                print(f"\n📋 Video ID 5 exists:")
                print(f"   ID {id_video.id}: {id_video.slug} | {id_video.title or 'NO TITLE'} | {id_video.status} | {'✅' if id_video.public else '❌'}")
            else:
                print(f"\n❌ Video ID 5 does not exist")
                
        else:
            print(f"❌ No video found with slug: {slug}")
            
            # Try to find any video with similar pattern
            print(f"\n🔍 Searching for similar videos...")
            similar_query = text("""
                SELECT id, slug, title, status, public 
                FROM videos 
                WHERE slug LIKE :pattern OR title LIKE :title_pattern
                ORDER BY id DESC
                LIMIT 10
            """)
            
            similar_result = session.execute(similar_query, {
                "pattern": "%abstract%", 
                "title_pattern": "%abstract%"
            })
            similar_videos = similar_result.fetchall()
            
            if similar_videos:
                print(f"📋 Found {len(similar_videos)} videos with 'abstract' in slug or title:")
                for v in similar_videos:
                    print(f"   ID {v.id}: {v.slug} | {v.title or 'NO TITLE'} | {v.status} | {'✅' if v.public else '❌'}")
            else:
                print(f"   No similar videos found")
        
    except Exception as e:
        print(f"❌ Error during search: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    main() 