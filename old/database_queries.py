#!/usr/bin/env python3
"""
Useful SQL queries for managing the videos table
"""
import psycopg2

# Configuration
CLOUD_SQL_CONFIG = {
    'host': '34.46.33.136',
    'database': 'prompttovideo',
    'user': 'prompttovideo',
    'password': 'PromptToVideo2024!',
    'port': 5432
}

def show_useful_queries():
    """Show useful SQL queries for managing videos table"""
    
    print("🔍 ===== USEFUL SQL QUERIES FOR VIDEOS TABLE =====")
    print()
    
    print("📋 1. VIEW ALL VIDEOS (Basic Info):")
    print("""
SELECT id, title, prompt, quality, status, views, created_at
FROM videos 
ORDER BY id;
""")
    
    print("📋 2. VIEW ALL VIDEOS (Full Details):")
    print("""
SELECT id, title, prompt, quality, status, views, 
       gcs_url, gcs_signed_url, thumbnail_url, thumbnail_gcs_url,
       public, user_id, created_at
FROM videos 
ORDER BY id;
""")
    
    print("📋 3. VIEW VIDEOS BY STATUS:")
    print("""
SELECT id, title, status, created_at
FROM videos 
WHERE status = 'completed'
ORDER BY id;
""")
    
    print("📋 4. VIEW VIDEOS WITH MISSING THUMBNAILS:")
    print("""
SELECT id, title, thumbnail_url IS NULL as missing_thumbnail
FROM videos 
WHERE thumbnail_url IS NULL
ORDER BY id;
""")
    
    print("📋 5. UPDATE VIDEO TITLE:")
    print("""
UPDATE videos 
SET title = 'New Title Here'
WHERE id = 1;
""")
    
    print("📋 6. UPDATE VIDEO PROMPT:")
    print("""
UPDATE videos 
SET prompt = 'New prompt text here'
WHERE id = 1;
""")
    
    print("📋 7. UPDATE MULTIPLE VIDEOS AT ONCE:")
    print("""
UPDATE videos 
SET title = 'Updated Title'
WHERE id IN (1, 2, 3);
""")
    
    print("📋 8. SET VIDEO TO PUBLIC:")
    print("""
UPDATE videos 
SET public = true
WHERE id = 1;
""")
    
    print("📋 9. INCREMENT VIEW COUNT:")
    print("""
UPDATE videos 
SET views = views + 1
WHERE id = 1;
""")
    
    print("📋 10. DELETE A VIDEO:")
    print("""
DELETE FROM videos 
WHERE id = 1;
""")
    
    print("📋 11. COUNT VIDEOS BY STATUS:")
    print("""
SELECT status, COUNT(*) as count
FROM videos 
GROUP BY status;
""")
    
    print("📋 12. FIND VIDEOS BY USER:")
    print("""
SELECT v.id, v.title, v.prompt, u.email
FROM videos v
JOIN users u ON v.user_id = u.id
WHERE u.email = 'test@example.com';
""")
    
    print("📋 13. SEARCH VIDEOS BY TITLE:")
    print("""
SELECT id, title, prompt
FROM videos 
WHERE title ILIKE '%monkey%'
ORDER BY id;
""")
    
    print("📋 14. GET MOST VIEWED VIDEOS:")
    print("""
SELECT id, title, views
FROM videos 
ORDER BY views DESC
LIMIT 10;
""")
    
    print("📋 15. GET RECENT VIDEOS:")
    print("""
SELECT id, title, created_at
FROM videos 
ORDER BY created_at DESC
LIMIT 10;
""")

def show_current_data():
    """Show current data in videos table"""
    conn = None
    try:
        conn = psycopg2.connect(**CLOUD_SQL_CONFIG)
        cursor = conn.cursor()
        
        print("📊 ===== CURRENT VIDEOS DATA =====")
        
        # Get basic info
        cursor.execute("""
            SELECT id, title, prompt, quality, status, views, created_at
            FROM videos 
            ORDER BY id
        """)
        
        videos = cursor.fetchall()
        
        print(f"Total videos: {len(videos)}")
        print()
        print("ID | Title | Prompt | Quality | Status | Views | Created")
        print("-" * 80)
        
        for video_id, title, prompt, quality, status, views, created_at in videos:
            title_short = title[:20] + "..." if title and len(title) > 20 else title or "None"
            prompt_short = prompt[:30] + "..." if prompt and len(prompt) > 30 else prompt or "None"
            print(f"{video_id:2} | {title_short:20} | {prompt_short:30} | {quality:6} | {status:9} | {views:5} | {created_at}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    show_current_data()
    print()
    show_useful_queries() 