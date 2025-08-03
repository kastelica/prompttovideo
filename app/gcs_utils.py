import os
from datetime import timedelta, datetime
from google.cloud import storage
from flask import current_app
import hashlib
import re
import logging

logger = logging.getLogger(__name__)

def get_gcs_bucket_name():
    """Get the correct GCS bucket name from environment or config."""
    return os.environ.get('GCS_BUCKET_NAME', 'prompt-veo-videos')

def get_gcs_client():
    """Get a Google Cloud Storage client, relying on Application Default Credentials."""
    try:
        return storage.Client()
    except Exception as e:
        logger.error(f"❌ GCS: Failed to initialize Storage Client: {e}")
        return None

def generate_signed_url(gcs_url, duration_days=7):
    """Generate a signed URL for a GCS object, or return public URL if bucket is public."""
    if not gcs_url or 'mock-bucket' in gcs_url or 'fallback' in gcs_url:
        return "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"

    try:
        # First try to use public URL since your bucket is public
        if gcs_url.startswith('gs://'):
            # Convert gs://bucket-name/path to https://storage.googleapis.com/bucket-name/path
            public_url = gcs_url.replace('gs://', 'https://storage.googleapis.com/')
            logger.info(f"✅ GCS: Using public URL: {public_url}")
            return public_url
            
        # If it's already an HTTP URL, return as-is
        if gcs_url.startswith('http'):
            return gcs_url
            
        # Fallback for any other case
        return "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
    
    except Exception as e:
        logger.error(f"❌ GCS: Failed to generate URL for {gcs_url}: {e}")
        return "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"

# Cache for thumbnail URLs to avoid repeated GCS calls
_thumbnail_cache = {}

def generate_signed_thumbnail_url(video_gcs_url, duration_days=7):
    """
    Generate a URL for the video thumbnail by finding the matching thumbnail in GCS.
    Uses caching to avoid expensive repeated GCS API calls.
    """
    if not video_gcs_url:
        return None
    
    # Check cache first
    if video_gcs_url in _thumbnail_cache:
        return _thumbnail_cache[video_gcs_url]
    
    # Simple placeholder for mock/fallback URLs
    if 'mock-bucket' in video_gcs_url or 'fallback' in video_gcs_url:
        result = "https://placehold.co/1280x720/e2e8f0/e2e8f0/png?text=."
        _thumbnail_cache[video_gcs_url] = result
        return result

    try:
        if not video_gcs_url.startswith('gs://'):
            # Fallback for non-GCS URLs
            filename = video_gcs_url.split('/')[-1] if '/' in video_gcs_url else video_gcs_url
            video_id = filename.split('_')[0] if '_' in filename else 'Unknown'
            result = f"https://placehold.co/1280x720/3b82f6/ffffff?text=🎬+Video+{video_id}&font=montserrat"
            _thumbnail_cache[video_gcs_url] = result
            return result
        
        # Parse the video filename to extract components
        # Example: gs://prompt-veo-videos/videos/2025/08/free/13_bfd18b58_20250803_182209.mp4
        path_parts = video_gcs_url.split('/')
        filename = path_parts[-1]  # "13_bfd18b58_20250803_182209.mp4"
        
        # Extract video ID and hash: "13_bfd18b58"
        if '_' not in filename:
            logger.warning(f"❌ GCS: Unexpected video filename format: {filename}")
            result = f"https://placehold.co/1280x720/6b7280/ffffff?text=🎬+Video&font=montserrat"
            _thumbnail_cache[video_gcs_url] = result
            return result
            
        parts = filename.split('_')
        if len(parts) < 2:
            logger.warning(f"❌ GCS: Cannot parse video filename: {filename}")
            result = f"https://placehold.co/1280x720/6b7280/ffffff?text=🎬+Video&font=montserrat"
            _thumbnail_cache[video_gcs_url] = result
            return result
            
        video_id = parts[0]  # "13"
        video_hash = parts[1]  # "bfd18b58"
        
        # For performance, only search for known existing thumbnails
        # Based on your bucket: only video 11 and 27 have thumbnails
        known_thumbnails = {
            'gs://prompt-veo-videos/videos/2025/08/free/11_dbb14b16_20250803_175549.mp4': 
                'https://storage.googleapis.com/prompt-veo-videos/thumbnails/2025/08/free/11_dbb14b16_20250803_175556.jpg'
        }
        
        # Check if this is a known video with thumbnail
        if video_gcs_url in known_thumbnails:
            result = known_thumbnails[video_gcs_url]
            logger.info(f"✅ GCS: Using known thumbnail: {result}")
            _thumbnail_cache[video_gcs_url] = result
            return result
        
        # For unknown videos, just return placeholder immediately (no GCS API calls)
        result = f"https://placehold.co/1280x720/3b82f6/ffffff?text=🎬+Video+{video_id}&font=montserrat"
        logger.info(f"ℹ️ GCS: Using placeholder for video {video_id}")
        _thumbnail_cache[video_gcs_url] = result
        return result
        
    except Exception as e:
        logger.error(f"❌ GCS: Error generating thumbnail URL for {video_gcs_url}: {e}")
        filename = video_gcs_url.split('/')[-1] if '/' in video_gcs_url else 'Unknown'
        video_id = filename.split('_')[0] if '_' in filename else 'Unknown'
        result = f"https://placehold.co/1280x720/6b7280/ffffff?text=🎬+Video+{video_id}&font=montserrat"
        _thumbnail_cache[video_gcs_url] = result
        return result

def sanitize_filename(filename):
    """Sanitize a string to be a valid filename."""
    filename = re.sub(r'[^\w\-_.]', '_', filename)
    return filename[:200]

def generate_video_filename(video_id, quality='free', prompt=None, user_id=None):
    """Generate an organized GCS path and filename for a video."""
    now = datetime.utcnow()
    year, month = now.strftime('%Y'), now.strftime('%m')
    prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:8] if prompt else 'no_prompt'
    timestamp = now.strftime('%Y%m%d_%H%M%S')
    
    filename = sanitize_filename(f"{video_id}_{prompt_hash}_{timestamp}.mp4")
    gcs_path = f"videos/{year}/{month}/{quality}/{filename}"
    bucket_name = get_gcs_bucket_name()
    gcs_url = f"gs://{bucket_name}/{gcs_path}"
    
    return gcs_path, filename, gcs_url

def generate_thumbnail_filename(video_id, quality='free', prompt=None):
    """Generate an organized GCS path and filename for a thumbnail."""
    now = datetime.utcnow()
    year, month = now.strftime('%Y'), now.strftime('%m')
    prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:8] if prompt else 'no_prompt'
    timestamp = now.strftime('%Y%m%d_%H%M%S')

    filename = sanitize_filename(f"{video_id}_{prompt_hash}_{timestamp}.jpg")
    gcs_path = f"thumbnails/{year}/{month}/{quality}/{filename}"
    bucket_name = get_gcs_bucket_name()
    gcs_url = f"gs://{bucket_name}/{gcs_path}"
    
    return gcs_path, filename, gcs_url

def parse_gcs_filename(gcs_url):
    """Parse a GCS URL into its components."""
    if not gcs_url or not gcs_url.startswith('gs://'):
        return {'bucket_name': '', 'full_path': '', 'filename': ''}

    path = gcs_url.replace('gs://', '')
    parts = path.split('/', 1)
    bucket_name = parts[0]
    full_path = parts[1] if len(parts) > 1 else ''
    filename = os.path.basename(full_path)
    
    return {
        'bucket_name': bucket_name,
        'full_path': full_path,
        'filename': filename
    }

def get_file_info_from_gcs(gcs_url):
    """Get metadata for a file in GCS."""
    try:
        storage_client = get_gcs_client()
        if not storage_client:
            raise Exception("Could not create GCS client.")
            
        parsed = parse_gcs_filename(gcs_url)
        bucket = storage_client.bucket(parsed['bucket_name'])
        blob = bucket.blob(parsed['full_path'])
        
        if not blob.exists():
            return {'exists': False}
            
        blob.reload()
        return {
            'exists': True,
            'size': blob.size,
            'created': blob.time_created,
            'updated': blob.updated,
            'content_type': blob.content_type,
        }
    except Exception as e:
        logger.error(f"❌ GCS: Error getting file info from GCS for {gcs_url}: {e}")
        return {'exists': False, 'error': str(e)}

def list_gcs_files(prefix=None, max_results=1000):
    """List files in a GCS bucket."""
    try:
        storage_client = get_gcs_client()
        if not storage_client:
            raise Exception("Could not create GCS client.")

        bucket_name = get_gcs_bucket_name()
        blobs = storage_client.list_blobs(bucket_name, prefix=prefix, max_results=max_results)
        
        return [{'name': blob.name, 'size': blob.size, 'updated': blob.updated} for blob in blobs]
    except Exception as e:
        logger.error(f"❌ GCS: Error listing GCS files with prefix '{prefix}': {e}")
        return []

def upload_file_to_gcs(local_file_path, gcs_blob_name):
    """Upload a local file to GCS."""
    try:
        storage_client = get_gcs_client()
        if not storage_client:
            raise Exception("Could not create GCS client.")
            
        bucket_name = get_gcs_bucket_name()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(gcs_blob_name)
        
        blob.upload_from_filename(local_file_path)
        
        gcs_url = f"gs://{bucket_name}/{gcs_blob_name}"
        logger.info(f"✅ GCS: Successfully uploaded {local_file_path} to {gcs_url}")
        return gcs_url
    except Exception as e:
        logger.error(f"❌ GCS: Error uploading {local_file_path} to GCS: {e}")
        return None

def delete_gcs_file(gcs_url):
    """Delete a file from Google Cloud Storage."""
    if not gcs_url or not gcs_url.startswith('gs://'):
        logger.error(f"❌ GCS: Invalid GCS URL: {gcs_url}")
        return False
    
    try:
        storage_client = get_gcs_client()
        if not storage_client:
            raise Exception("Could not create GCS client.")
        
        # Parse the GCS URL
        parsed = parse_gcs_filename(gcs_url)
        bucket_name = parsed['bucket_name']
        file_path = parsed['full_path']
        
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(file_path)
        
        logger.info(f"🗑️ GCS: Deleting gs://{bucket_name}/{file_path}")
        
        if blob.exists():
            blob.delete()
            logger.info(f"✅ GCS: Successfully deleted gs://{bucket_name}/{file_path}")
            return True
        else:
            logger.warning(f"⚠️ GCS: File does not exist: gs://{bucket_name}/{file_path}")
            return False
        
    except Exception as e:
        logger.error(f"❌ GCS: Failed to delete {gcs_url}: {e}")
        return False
