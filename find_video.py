#!/usr/bin/env python3
"""
Find Video Script

This script searches for a specific video by title in the database.
"""

import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app, db
from app.models import Video, User
from sqlalchemy import or_

def find_video_by_title():
    """Search for video with title 'Bblyrics in Recycle bin'"""
    print("🔍 ===== SEARCHING FOR VIDEO =====")
    print("Searching for: 'Bblyrics in Recycle bin'")
    print()
    
    app = create_app()
    with app.app_context():
        # Search for the exact title
        exact_match = Video.query.filter_by(title='Bblyrics in Recycle bin').first()
        
        # Search for partial matches
        partial_matches = Video.query.filter(
            or_(
                Video.title.contains('Bblyrics'),
                Video.title.contains('Recycle'),
                Video.title.contains('bin')
            )
        ).all()
        
        # Search for similar titles
        similar_matches = Video.query.filter(
            or_(
                Video.title.contains('bblyrics'),
                Video.title.contains('recycle'),
                Video.title.contains('Bin')
            )
        ).all()
        
        print("📊 ===== SEARCH RESULTS =====")
        print()
        
        if exact_match:
            print("✅ EXACT MATCH FOUND:")
            print(f"   - ID: {exact_match.id}")
            print(f"   - Title: '{exact_match.title}'")
            print(f"   - Status: {exact_match.status}")
            print(f"   - User ID: {exact_match.user_id}")
            print(f"   - Public: {exact_match.public}")
            print(f"   - GCS URL: {bool(exact_match.gcs_url)}")
            print(f"   - Signed URL: {bool(exact_match.gcs_signed_url)}")
            print(f"   - Created: {exact_match.created_at}")
            print(f"   - Prompt: '{exact_match.prompt}'")
            print()
        else:
            print("❌ No exact match found for 'Bblyrics in Recycle bin'")
            print()
        
        if partial_matches:
            print("🔍 PARTIAL MATCHES (case-sensitive):")
            for video in partial_matches:
                print(f"   - ID: {video.id}, Title: '{video.title}', Status: {video.status}")
            print()
        else:
            print("❌ No partial matches found (case-sensitive)")
            print()
        
        if similar_matches:
            print("🔍 SIMILAR MATCHES (case-insensitive):")
            for video in similar_matches:
                print(f"   - ID: {video.id}, Title: '{video.title}', Status: {video.status}")
            print()
        else:
            print("❌ No similar matches found (case-insensitive)")
            print()
        
        # Show all videos for comparison
        all_videos = Video.query.all()
        print(f"📋 ===== ALL VIDEOS IN DATABASE ({len(all_videos)}) =====")
        for video in all_videos:
            print(f"   - ID: {video.id}, Title: '{video.title}', Status: {video.status}")
        
        print()
        print("🎯 ===== SUMMARY =====")
        print(f"Total videos in database: {len(all_videos)}")
        print(f"Exact match found: {'Yes' if exact_match else 'No'}")
        print(f"Partial matches found: {len(partial_matches)}")
        print(f"Similar matches found: {len(similar_matches)}")

if __name__ == "__main__":
    find_video_by_title() 