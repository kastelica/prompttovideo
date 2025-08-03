import os
import sys
from datetime import datetime, timezone

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app, db
from app.models import Video, User
from app.gcs_utils import get_file_info_from_gcs, generate_signed_url

# Force production environment
os.environ['FLASK_ENV'] = 'production'
os.environ['FLASK_DEBUG'] = '0'

# Set Cloud SQL connection string
os.environ['DATABASE_URL'] = 'postgresql://prompttovideo:PromptToVideo2024!@34.46.33.136:5432/prompttovideo'

def check_gcs_file_exists(gcs_url):
    """Check if a GCS file exists"""
    try:
        info = get_file_info_from_gcs(gcs_url)
        return info is not None
    except Exception as e:
        return False

def analyze_video_urls():
    """Analyze video URLs in the database"""
    print("🔍 ANALYZING CLOUD SQL VIDEO & THUMBNAIL URLS")
    print("=" * 60)
    
    app = create_app()
    with app.app_context():
        # Get all videos
        videos = Video.query.order_by(Video.created_at.desc()).all()
        
        if not videos:
            print("❌ No videos found in database")
            return
        
        print(f"✅ Found {len(videos)} videos in database")
        print()
        
        # Statistics
        stats = {
            'total_videos': len(videos),
            'videos_with_gcs_url': 0,
            'videos_with_signed_url': 0,
            'videos_with_thumbnail_url': 0,
            'videos_with_thumbnail_gcs_url': 0,
            'gcs_urls_exist': 0,
            'thumbnail_gcs_urls_exist': 0,
            'signed_urls_valid': 0,
            'thumbnail_urls_valid': 0,
            'issues': []
        }
        
        # Analyze each video
        for i, video in enumerate(videos):
            print(f"🎬 Video {i+1}/{len(videos)} (ID: {video.id})")
            print(f"   Title: {video.title or 'N/A'}")
            print(f"   Prompt: {video.prompt[:80]}...")
            print(f"   Status: {video.status}")
            print(f"   Created: {video.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Check video URLs
            print("   📹 Video URLs:")
            if video.gcs_url:
                stats['videos_with_gcs_url'] += 1
                print(f"      GCS URL: {video.gcs_url}")
                
                # Check if GCS file exists
                gcs_exists = check_gcs_file_exists(video.gcs_url)
                if gcs_exists:
                    stats['gcs_urls_exist'] += 1
                    print(f"      ✅ GCS file exists")
                else:
                    print(f"      ❌ GCS file NOT found")
                    stats['issues'].append({
                        'video_id': video.id,
                        'type': 'missing_gcs_video',
                        'url': video.gcs_url
                    })
            else:
                print(f"      ❌ No GCS URL")
                stats['issues'].append({
                    'video_id': video.id,
                    'type': 'no_gcs_url',
                    'url': None
                })
            
            if video.gcs_signed_url:
                stats['videos_with_signed_url'] += 1
                print(f"      Signed URL: {video.gcs_signed_url[:80]}...")
                
                # Check if signed URL is recent (not expired)
                if 'X-Goog-Expires' in video.gcs_signed_url:
                    print(f"      ✅ Has signed URL")
                    stats['signed_urls_valid'] += 1
                else:
                    print(f"      ⚠️ Signed URL may be expired")
            else:
                print(f"      ❌ No signed URL")
                stats['issues'].append({
                    'video_id': video.id,
                    'type': 'no_signed_url',
                    'url': None
                })
            
            # Check thumbnail URLs
            print("   🖼️ Thumbnail URLs:")
            if video.thumbnail_gcs_url:
                stats['videos_with_thumbnail_gcs_url'] += 1
                print(f"      Thumbnail GCS: {video.thumbnail_gcs_url}")
                
                # Check if thumbnail GCS file exists
                thumb_gcs_exists = check_gcs_file_exists(video.thumbnail_gcs_url)
                if thumb_gcs_exists:
                    stats['thumbnail_gcs_urls_exist'] += 1
                    print(f"      ✅ Thumbnail GCS file exists")
                else:
                    print(f"      ❌ Thumbnail GCS file NOT found")
                    stats['issues'].append({
                        'video_id': video.id,
                        'type': 'missing_thumbnail_gcs',
                        'url': video.thumbnail_gcs_url
                    })
            else:
                print(f"      ❌ No thumbnail GCS URL")
                stats['issues'].append({
                    'video_id': video.id,
                    'type': 'no_thumbnail_gcs_url',
                    'url': None
                })
            
            if video.thumbnail_url:
                stats['videos_with_thumbnail_url'] += 1
                print(f"      Thumbnail URL: {video.thumbnail_url[:80]}...")
                
                # Check if it's a GCS URL that needs conversion
                if video.thumbnail_url.startswith('gs://'):
                    print(f"      ⚠️ Thumbnail URL is GCS format (needs conversion)")
                    stats['issues'].append({
                        'video_id': video.id,
                        'type': 'thumbnail_gcs_format',
                        'url': video.thumbnail_url
                    })
                else:
                    print(f"      ✅ Thumbnail URL is public format")
                    stats['thumbnail_urls_valid'] += 1
            else:
                print(f"      ❌ No thumbnail URL")
                stats['issues'].append({
                    'video_id': video.id,
                    'type': 'no_thumbnail_url',
                    'url': None
                })
            
            # Test get_thumbnail_url method
            try:
                display_url = video.get_thumbnail_url()
                if display_url:
                    print(f"      ✅ get_thumbnail_url() returns: {display_url[:80]}...")
                else:
                    print(f"      ❌ get_thumbnail_url() returns None")
                    stats['issues'].append({
                        'video_id': video.id,
                        'type': 'get_thumbnail_url_fails',
                        'url': None
                    })
            except Exception as e:
                print(f"      ❌ get_thumbnail_url() error: {str(e)}")
                stats['issues'].append({
                    'video_id': video.id,
                    'type': 'get_thumbnail_url_error',
                    'error': str(e)
                })
            
            print()
        
        # Print summary statistics
        print("📊 SUMMARY STATISTICS")
        print("=" * 60)
        print(f"Total videos: {stats['total_videos']}")
        print(f"Videos with GCS URL: {stats['videos_with_gcs_url']} ({stats['videos_with_gcs_url']/stats['total_videos']*100:.1f}%)")
        print(f"Videos with signed URL: {stats['videos_with_signed_url']} ({stats['videos_with_signed_url']/stats['total_videos']*100:.1f}%)")
        print(f"Videos with thumbnail URL: {stats['videos_with_thumbnail_url']} ({stats['videos_with_thumbnail_url']/stats['total_videos']*100:.1f}%)")
        print(f"Videos with thumbnail GCS URL: {stats['videos_with_thumbnail_gcs_url']} ({stats['videos_with_thumbnail_gcs_url']/stats['total_videos']*100:.1f}%)")
        print()
        print(f"GCS video files exist: {stats['gcs_urls_exist']} ({stats['gcs_urls_exist']/stats['videos_with_gcs_url']*100:.1f}% of videos with GCS URL)")
        print(f"GCS thumbnail files exist: {stats['thumbnail_gcs_urls_exist']} ({stats['thumbnail_gcs_urls_exist']/stats['videos_with_thumbnail_gcs_url']*100:.1f}% of videos with thumbnail GCS URL)")
        print(f"Valid signed URLs: {stats['signed_urls_valid']} ({stats['signed_urls_valid']/stats['videos_with_signed_url']*100:.1f}% of videos with signed URL)")
        print(f"Valid thumbnail URLs: {stats['thumbnail_urls_valid']} ({stats['thumbnail_urls_valid']/stats['videos_with_thumbnail_url']*100:.1f}% of videos with thumbnail URL)")
        
        # Print issues
        if stats['issues']:
            print()
            print("🚨 ISSUES FOUND")
            print("=" * 60)
            
            issue_types = {}
            for issue in stats['issues']:
                issue_type = issue['type']
                if issue_type not in issue_types:
                    issue_types[issue_type] = []
                issue_types[issue_type].append(issue)
            
            for issue_type, issues in issue_types.items():
                print(f"\n{issue_type.upper()} ({len(issues)} videos):")
                for issue in issues[:5]:  # Show first 5 examples
                    print(f"  - Video ID {issue['video_id']}")
                    if 'url' in issue and issue['url']:
                        print(f"    URL: {issue['url']}")
                    if 'error' in issue:
                        print(f"    Error: {issue['error']}")
                if len(issues) > 5:
                    print(f"  ... and {len(issues) - 5} more")
        else:
            print()
            print("✅ No issues found! All URLs appear to be valid.")
        
        print()
        print("🎯 RECOMMENDATIONS:")
        print("=" * 60)
        
        if stats['issues']:
            if any(issue['type'] == 'missing_gcs_video' for issue in stats['issues']):
                print("• Run video mapping script to fix missing GCS video URLs")
            if any(issue['type'] == 'missing_thumbnail_gcs' for issue in stats['issues']):
                print("• Regenerate thumbnails for videos with missing thumbnail GCS files")
            if any(issue['type'] == 'thumbnail_gcs_format' for issue in stats['issues']):
                print("• Convert thumbnail URLs from GCS format to public URLs")
            if any(issue['type'] == 'no_signed_url' for issue in stats['issues']):
                print("• Update signed URLs for videos missing them")
        else:
            print("• All URLs appear to be valid and accessible")
        
        print("✅ URL analysis completed!")

def main():
    print("🔍 CLOUD SQL URL COMPARISON TOOL")
    print("=" * 50)
    
    try:
        analyze_video_urls()
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main() 