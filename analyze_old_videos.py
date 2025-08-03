#!/usr/bin/env python3
"""
Analyze old videos to identify candidates for removal.
"""

import os
import sys
from datetime import datetime, timedelta
from sqlalchemy import and_, or_

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app, db
from app.models import Video, User

def analyze_old_videos():
    """Analyze videos and identify candidates for removal."""
    
    app = create_app()
    
    with app.app_context():
        print("🔍 ANALYZING OLD VIDEOS FOR REMOVAL CANDIDATES")
        print("=" * 60)
        
        # Get all videos
        all_videos = Video.query.all()
        print(f"📊 Total videos in database: {len(all_videos)}")
        
        # Define criteria for removal candidates
        candidates = {
            'missing_thumbnails': [],
            'low_views': [],
            'old_videos': [],
            'test_videos': [],
            'failed_videos': [],
            'duplicate_prompts': [],
            'very_old': []
        }
        
        # Calculate dates
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        three_months_ago = now - timedelta(days=90)
        
        for video in all_videos:
            # 1. Missing thumbnails
            if not video.get_thumbnail_url():
                candidates['missing_thumbnails'].append(video)
            
            # 2. Low view count (less than 5 views)
            if video.views and video.views < 5:
                candidates['low_views'].append(video)
            
            # 3. Old videos (older than 1 month)
            if video.created_at < month_ago:
                candidates['old_videos'].append(video)
            
            # 4. Very old videos (older than 3 months)
            if video.created_at < three_months_ago:
                candidates['very_old'].append(video)
            
            # 5. Test videos (prompt contains 'test')
            if video.prompt and 'test' in video.prompt.lower():
                candidates['test_videos'].append(video)
            
            # 6. Failed videos (status is failed or error)
            if video.status in ['failed', 'error', 'content_violation']:
                candidates['failed_videos'].append(video)
        
        # 7. Duplicate prompts (find videos with similar prompts)
        prompt_groups = {}
        for video in all_videos:
            if video.prompt:
                # Normalize prompt for comparison
                normalized = video.prompt.lower().strip()
                if normalized not in prompt_groups:
                    prompt_groups[normalized] = []
                prompt_groups[normalized].append(video)
        
        # Find duplicates
        for prompt, videos in prompt_groups.items():
            if len(videos) > 1:
                # Sort by creation date, keep the newest
                videos.sort(key=lambda v: v.created_at, reverse=True)
                candidates['duplicate_prompts'].extend(videos[1:])  # All except the newest
        
        # Print analysis results
        print("\n📋 REMOVAL CANDIDATES BY CATEGORY:")
        print("-" * 40)
        
        total_candidates = 0
        
        for category, videos in candidates.items():
            if videos:
                print(f"\n🔴 {category.replace('_', ' ').title()}: {len(videos)} videos")
                total_candidates += len(videos)
                
                # Show first 3 examples
                for i, video in enumerate(videos[:3]):
                    user_email = video.user.email if video.user else "Unknown"
                    print(f"   {i+1}. ID {video.id}: '{video.prompt[:50]}...' by {user_email}")
                    print(f"      Status: {video.status}, Views: {video.views}, Created: {video.created_at.strftime('%Y-%m-%d')}")
                
                if len(videos) > 3:
                    print(f"   ... and {len(videos) - 3} more")
        
        print(f"\n📊 SUMMARY:")
        print(f"   Total candidates: {total_candidates}")
        print(f"   Percentage of total: {(total_candidates/len(all_videos)*100):.1f}%")
        
        # Show detailed breakdown
        print(f"\n📈 DETAILED BREAKDOWN:")
        print("-" * 30)
        
        # Missing thumbnails
        if candidates['missing_thumbnails']:
            print(f"\n🔴 Missing Thumbnails ({len(candidates['missing_thumbnails'])}):")
            for video in candidates['missing_thumbnails']:
                user_email = video.user.email if video.user else "Unknown"
                print(f"   ID {video.id}: '{video.prompt[:40]}...' by {user_email}")
                print(f"      Status: {video.status}, Views: {video.views}, Created: {video.created_at.strftime('%Y-%m-%d')}")
        
        # Low views
        if candidates['low_views']:
            print(f"\n🔴 Low Views (< 5) ({len(candidates['low_views'])}):")
            for video in candidates['low_views']:
                user_email = video.user.email if video.user else "Unknown"
                print(f"   ID {video.id}: '{video.prompt[:40]}...' by {user_email}")
                print(f"      Views: {video.views}, Created: {video.created_at.strftime('%Y-%m-%d')}")
        
        # Test videos
        if candidates['test_videos']:
            print(f"\n🔴 Test Videos ({len(candidates['test_videos'])}):")
            for video in candidates['test_videos']:
                user_email = video.user.email if video.user else "Unknown"
                print(f"   ID {video.id}: '{video.prompt}' by {user_email}")
                print(f"      Status: {video.status}, Views: {video.views}, Created: {video.created_at.strftime('%Y-%m-%d')}")
        
        # Failed videos
        if candidates['failed_videos']:
            print(f"\n🔴 Failed Videos ({len(candidates['failed_videos'])}):")
            for video in candidates['failed_videos']:
                user_email = video.user.email if video.user else "Unknown"
                print(f"   ID {video.id}: '{video.prompt[:40]}...' by {user_email}")
                print(f"      Status: {video.status}, Created: {video.created_at.strftime('%Y-%m-%d')}")
        
        # Very old videos
        if candidates['very_old']:
            print(f"\n🔴 Very Old (> 3 months) ({len(candidates['very_old'])}):")
            for video in candidates['very_old']:
                user_email = video.user.email if video.user else "Unknown"
                days_old = (now - video.created_at).days
                print(f"   ID {video.id}: '{video.prompt[:40]}...' by {user_email}")
                print(f"      {days_old} days old, Views: {video.views}, Status: {video.status}")
        
        # Duplicate prompts
        if candidates['duplicate_prompts']:
            print(f"\n🔴 Duplicate Prompts ({len(candidates['duplicate_prompts'])}):")
            for video in candidates['duplicate_prompts']:
                user_email = video.user.email if video.user else "Unknown"
                print(f"   ID {video.id}: '{video.prompt[:40]}...' by {user_email}")
                print(f"      Views: {video.views}, Created: {video.created_at.strftime('%Y-%m-%d')}")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        print("-" * 20)
        
        if candidates['failed_videos']:
            print("✅ HIGH PRIORITY: Remove failed/error videos - they're not useful")
        
        if candidates['test_videos']:
            print("✅ HIGH PRIORITY: Remove test videos - they're not real content")
        
        if candidates['missing_thumbnails']:
            print("⚠️  MEDIUM PRIORITY: Consider removing videos with missing thumbnails")
        
        if candidates['very_old']:
            print("⚠️  MEDIUM PRIORITY: Consider removing very old videos (> 3 months) with low engagement")
        
        if candidates['duplicate_prompts']:
            print("⚠️  LOW PRIORITY: Consider removing duplicate prompts (keep the newest)")
        
        if candidates['low_views']:
            print("⚠️  LOW PRIORITY: Consider removing videos with very low views (< 5)")
        
        print(f"\n🎯 NEXT STEPS:")
        print("1. Review the candidates above")
        print("2. Decide which categories to remove")
        print("3. Use the video IDs to remove them manually or create a removal script")
        print("4. Consider backing up before bulk removal")

if __name__ == "__main__":
    analyze_old_videos() 