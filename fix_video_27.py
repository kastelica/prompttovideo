#!/usr/bin/env python3
"""
Fix Video 27 Script

This script makes video ID 27 public so it can be accessed on the watch page.
"""

from sqlalchemy import create_engine, text

def fix_video_27():
    """Make video ID 27 public"""
    print("🔧 ===== FIXING VIDEO ID 27 =====")
    
    # Connect to production database
    direct_url = "postgresql://prompttovideo:PromptToVideo2024!@34.46.33.136:5432/prompttovideo"
    
    try:
        engine = create_engine(direct_url)
        
        # Check current status
        print("📊 ===== CURRENT STATUS =====")
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, title, status, public, created_at, updated_at
                FROM videos 
                WHERE id = 27;
            """))
            video = result.fetchone()
            
            if video:
                print(f"Video ID: {video[0]}")
                print(f"Title: {video[1]}")
                print(f"Status: {video[2]}")
                print(f"Public: {video[3]}")
                print(f"Created: {video[4]}")
                print(f"Updated: {video[5]}")
            else:
                print("❌ Video ID 27 not found!")
                return
        
        print()
        print("🔧 ===== MAKING VIDEO PUBLIC =====")
        
        # Make video public
        with engine.connect() as conn:
            result = conn.execute(text("""
                UPDATE videos 
                SET public = true, updated_at = NOW()
                WHERE id = 27;
            """))
            conn.commit()
            
            print("✅ Video ID 27 is now public!")
        
        # Verify the change
        print()
        print("📊 ===== VERIFICATION =====")
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, title, status, public, created_at, updated_at
                FROM videos 
                WHERE id = 27;
            """))
            video = result.fetchone()
            
            if video:
                print(f"Video ID: {video[0]}")
                print(f"Title: {video[1]}")
                print(f"Status: {video[2]}")
                print(f"Public: {video[3]} ✅")
                print(f"Created: {video[4]}")
                print(f"Updated: {video[5]}")
        
        print()
        print("🎉 ===== SUCCESS =====")
        print("Video ID 27 is now public and should be accessible at:")
        print("https://prompt-videos.com/watch/27-27-2-people-in-love")
        print()
        print("If the URL doesn't work, try:")
        print("1. Check the correct slug in the database")
        print("2. Wait a few minutes for changes to propagate")
        print("3. Clear any caching")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    fix_video_27() 