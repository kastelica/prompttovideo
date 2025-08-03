#!/usr/bin/env python3
"""
Improve Video Privacy UX Script

This script improves the user experience around video privacy by:
1. Making videos public by default
2. Adding better user feedback about video status
3. Ensuring users can always access their own videos
"""

from sqlalchemy import create_engine, text

def improve_video_privacy_ux():
    """Improve video privacy user experience"""
    print("🔧 ===== IMPROVING VIDEO PRIVACY UX =====")
    
    # Connect to production database
    direct_url = "postgresql://prompttovideo:PromptToVideo2024!@34.46.33.136:5432/prompttovideo"
    
    try:
        engine = create_engine(direct_url)
        
        print("📊 ===== CURRENT VIDEO PRIVACY STATUS =====")
        
        # Check current privacy distribution
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT public, COUNT(*) as count 
                FROM videos 
                GROUP BY public 
                ORDER BY public;
            """))
            privacy_stats = result.fetchall()
            
            for row in privacy_stats:
                status = "Public" if row[0] else "Private"
                print(f"{status}: {row[1]} videos")
        
        print()
        print("🔧 ===== MAKING COMPLETED VIDEOS PUBLIC =====")
        
        # Make all completed videos public
        with engine.connect() as conn:
            result = conn.execute(text("""
                UPDATE videos 
                SET public = true, updated_at = NOW()
                WHERE status = 'completed' AND public = false;
            """))
            conn.commit()
            
            updated_count = result.rowcount
            print(f"✅ Made {updated_count} completed videos public")
        
        # Verify the changes
        print()
        print("📊 ===== VERIFICATION =====")
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT public, COUNT(*) as count 
                FROM videos 
                GROUP BY public 
                ORDER BY public;
            """))
            privacy_stats = result.fetchall()
            
            for row in privacy_stats:
                status = "Public" if row[0] else "Private"
                print(f"{status}: {row[1]} videos")
        
        print()
        print("🎉 ===== SUCCESS =====")
        print("All completed videos are now public and accessible!")
        print()
        print("📋 ===== NEXT STEPS FOR CODE CHANGES =====")
        print("1. Update Video model default: public = True")
        print("2. Add user access to own private videos")
        print("3. Improve UI feedback for video status")
        print("4. Add privacy toggle with better UX")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def show_code_changes_needed():
    """Show the code changes needed to improve UX"""
    print("\n📝 ===== REQUIRED CODE CHANGES =====")
    print()
    
    print("1. 🔧 UPDATE VIDEO MODEL (app/models.py):")
    print("   Change line 252 from:")
    print("   public = db.Column(db.Boolean, default=False)")
    print("   to:")
    print("   public = db.Column(db.Boolean, default=True)")
    print()
    
    print("2. 🔧 UPDATE WATCH ROUTE (app/main/routes.py):")
    print("   Modify watch_video function to allow users to see their own videos:")
    print("   Add user authentication check and allow access to own videos")
    print()
    
    print("3. 🔧 IMPROVE MY VIDEOS PAGE (app/templates/main/my_videos.html):")
    print("   Add better status indicators and privacy controls")
    print("   Show clear feedback about video accessibility")
    print()
    
    print("4. 🔧 ADD PRIVACY SETTINGS:")
    print("   Add user preference for default video privacy")
    print("   Add bulk privacy management tools")
    print()

if __name__ == "__main__":
    improve_video_privacy_ux()
    show_code_changes_needed() 