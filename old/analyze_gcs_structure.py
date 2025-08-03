#!/usr/bin/env python3
"""
GCS Bucket Structure Analysis and Organization Script

This script analyzes the current structure of the prompt-veo-videos bucket
and provides recommendations for better organization.
"""

import os
import sys
from datetime import datetime, timezone

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app, db
from app.models import Video
from app.gcs_utils import get_storage_stats, list_gcs_files, parse_gcs_filename

def analyze_current_structure():
    """Analyze the current GCS bucket structure"""
    print("🔍 ===== GCS BUCKET STRUCTURE ANALYSIS =====")
    print(f"📅 Analysis Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print()
    
    # Get storage statistics
    stats = get_storage_stats()
    
    if 'error' in stats:
        print(f"❌ Error getting storage stats: {stats['error']}")
        return
    
    print("📊 STORAGE STATISTICS:")
    print(f"   Total Files: {stats['total_files']}")
    print(f"   Total Size: {stats['total_size_gb']:.2f} GB ({stats['total_size_mb']:.1f} MB)")
    print(f"   Videos: {stats['videos_count']} files, {stats['videos_size_mb']:.1f} MB")
    print(f"   Thumbnails: {stats['thumbnails_count']} files, {stats['thumbnails_size_mb']:.1f} MB")
    print(f"   Organized Files: {stats['organized_files']}")
    print(f"   Legacy Files: {stats['legacy_files']}")
    print()
    
    # Analyze by quality
    if stats['by_quality']:
        print("🎬 FILES BY QUALITY:")
        for quality, data in stats['by_quality'].items():
            size_mb = data['size'] / (1024 * 1024)
            print(f"   {quality}: {data['count']} files, {size_mb:.1f} MB")
        print()
    
    # Analyze by year
    if stats['by_year']:
        print("📅 FILES BY YEAR:")
        for year, data in sorted(stats['by_year'].items()):
            size_mb = data['size'] / (1024 * 1024)
            print(f"   {year}: {data['count']} files, {size_mb:.1f} MB")
        print()
    
    # Analyze by month
    if stats['by_month']:
        print("📅 FILES BY MONTH:")
        for month, data in sorted(stats['by_month'].items()):
            size_mb = data['size'] / (1024 * 1024)
            print(f"   {month}: {data['count']} files, {size_mb:.1f} MB")
        print()

def analyze_file_patterns():
    """Analyze file naming patterns in the bucket"""
    print("🔍 ===== FILE PATTERN ANALYSIS =====")
    print()
    
    # List all files
    files = list_gcs_files()
    
    if not files:
        print("❌ No files found in bucket")
        return
    
    # Analyze patterns
    patterns = {
        'organized': [],
        'legacy': [],
        'unknown': []
    }
    
    for file_info in files:
        parsed = file_info['parsed_info']
        
        if parsed['is_organized']:
            patterns['organized'].append(file_info)
        elif 'file_type' in parsed and parsed['file_type'] in ['videos', 'thumbnails']:
            patterns['legacy'].append(file_info)
        else:
            # Check if it's a legacy file by path structure
            path_parts = parsed.get('path_parts', [])
            if len(path_parts) >= 1 and path_parts[0] in ['videos', 'thumbnails']:
                patterns['legacy'].append(file_info)
            else:
                patterns['unknown'].append(file_info)
    
    print(f"📁 FILE PATTERNS:")
    print(f"   Organized (new format): {len(patterns['organized'])} files")
    print(f"   Legacy (old format): {len(patterns['legacy'])} files")
    print(f"   Unknown patterns: {len(patterns['unknown'])} files")
    print()
    
    # Show examples of each pattern
    if patterns['legacy']:
        print("📁 LEGACY PATTERN EXAMPLES:")
        for i, file_info in enumerate(patterns['legacy'][:5]):
            print(f"   {i+1}. {file_info['name']}")
        if len(patterns['legacy']) > 5:
            print(f"   ... and {len(patterns['legacy']) - 5} more")
        print()
    
    if patterns['organized']:
        print("📁 ORGANIZED PATTERN EXAMPLES:")
        for i, file_info in enumerate(patterns['organized'][:5]):
            print(f"   {i+1}. {file_info['name']}")
        if len(patterns['organized']) > 5:
            print(f"   ... and {len(patterns['organized']) - 5} more")
        print()
    
    if patterns['unknown']:
        print("📁 UNKNOWN PATTERN EXAMPLES:")
        for i, file_info in enumerate(patterns['unknown'][:5]):
            print(f"   {i+1}. {file_info['name']}")
        if len(patterns['unknown']) > 5:
            print(f"   ... and {len(patterns['unknown']) - 5} more")
        print()

def analyze_database_vs_gcs():
    """Compare database records with GCS files"""
    print("🔍 ===== DATABASE vs GCS ANALYSIS =====")
    print()
    
    app = create_app()
    with app.app_context():
        # Get all videos from database
        db_videos = Video.query.all()
        
        print(f"📊 DATABASE STATISTICS:")
        print(f"   Total videos in database: {len(db_videos)}")
        
        # Count videos by status
        status_counts = {}
        for video in db_videos:
            status = video.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"   Videos by status:")
        for status, count in status_counts.items():
            print(f"     {status}: {count}")
        print()
        
        # Check GCS URLs
        videos_with_gcs = [v for v in db_videos if v.gcs_url and v.gcs_url.startswith('gs://')]
        videos_without_gcs = [v for v in db_videos if not v.gcs_url or not v.gcs_url.startswith('gs://')]
        
        print(f"📁 GCS URL ANALYSIS:")
        print(f"   Videos with GCS URLs: {len(videos_with_gcs)}")
        print(f"   Videos without GCS URLs: {len(videos_without_gcs)}")
        print()
        
        # Check thumbnail URLs
        videos_with_thumbnails = [v for v in db_videos if v.thumbnail_url and v.thumbnail_url.startswith('gs://')]
        videos_without_thumbnails = [v for v in db_videos if not v.thumbnail_url or not v.thumbnail_url.startswith('gs://')]
        
        print(f"🖼️ THUMBNAIL ANALYSIS:")
        print(f"   Videos with GCS thumbnails: {len(videos_with_thumbnails)}")
        print(f"   Videos without GCS thumbnails: {len(videos_without_thumbnails)}")
        print()

def provide_recommendations():
    """Provide recommendations for improving the GCS structure"""
    print("💡 ===== RECOMMENDATIONS =====")
    print()
    
    print("🎯 IMMEDIATE ACTIONS:")
    print("   1. Standardize bucket name across all files")
    print("      - Update config.py to use 'prompt-veo-videos'")
    print("      - Update environment variables")
    print()
    
    print("   2. Implement organized naming for new uploads")
    print("      - Use: videos/{year}/{month}/{quality}/{video_id}_{prompt_hash}_{timestamp}.mp4")
    print("      - Use: thumbnails/{year}/{month}/{quality}/{video_id}_{prompt_hash}_{timestamp}.jpg")
    print()
    
    print("   3. Generate missing thumbnails")
    print("      - Run thumbnail generation for videos without thumbnails")
    print("      - Use the new organized naming system")
    print()
    
    print("📋 MIGRATION STRATEGY:")
    print("   1. Phase 1: New uploads use organized naming")
    print("   2. Phase 2: Generate thumbnails for existing videos")
    print("   3. Phase 3: Optional migration of existing files to organized structure")
    print()
    
    print("🔧 TECHNICAL IMPROVEMENTS:")
    print("   1. Add file metadata (user_id, prompt, quality, etc.)")
    print("   2. Implement file lifecycle policies")
    print("   3. Add monitoring and analytics")
    print("   4. Implement backup and recovery procedures")
    print()
    
    print("📊 MONITORING:")
    print("   1. Track storage usage by quality and time period")
    print("   2. Monitor file access patterns")
    print("   3. Set up alerts for storage thresholds")
    print("   4. Regular cleanup of orphaned files")
    print()

def show_example_structure():
    """Show examples of the new organized structure"""
    print("📁 ===== NEW ORGANIZED STRUCTURE EXAMPLES =====")
    print()
    
    print("🎬 VIDEO FILES:")
    print("   videos/2024/12/free/123_a1b2c3d4_20241215_143022.mp4")
    print("   videos/2024/12/premium/124_e5f6g7h8_20241215_143045.mp4")
    print("   videos/2024/12/1080p/125_i9j0k1l2_20241215_143108.mp4")
    print()
    
    print("🖼️ THUMBNAIL FILES:")
    print("   thumbnails/2024/12/free/123_a1b2c3d4_20241215_143022.jpg")
    print("   thumbnails/2024/12/premium/124_e5f6g7h8_20241215_143045.jpg")
    print("   thumbnails/2024/12/1080p/125_i9j0k1l2_20241215_143108.jpg")
    print()
    
    print("📊 BENEFITS:")
    print("   ✅ Chronological organization")
    print("   ✅ Quality-based separation")
    print("   ✅ Easy to find related files")
    print("   ✅ Scalable for large volumes")
    print("   ✅ Better cost management")
    print("   ✅ Easier backup and recovery")
    print()

def main():
    """Main analysis function"""
    print("🚀 Starting GCS Bucket Structure Analysis...")
    print()
    
    try:
        # Run all analyses
        analyze_current_structure()
        analyze_file_patterns()
        analyze_database_vs_gcs()
        provide_recommendations()
        show_example_structure()
        
        print("✅ Analysis complete!")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        print(f"❌ Full traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    main() 