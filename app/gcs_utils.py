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
    """Generate a signed URL for a GCS object."""
    if not gcs_url or 'mock-bucket' in gcs_url or 'fallback' in gcs_url:
        return "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"

    try:
        storage_client = get_gcs_client()
        if not storage_client:
            raise Exception("Could not create GCS client.")

        parsed = parse_gcs_filename(gcs_url)
        bucket = storage_client.bucket(parsed['bucket_name'])
        blob = bucket.blob(parsed['full_path'])

        if not blob.exists():
            logger.warning(f"⚠️ GCS: Blob does not exist, cannot create signed URL for: {gcs_url}")
            return None

        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(days=duration_days),
            method="GET"
        )
        return signed_url
    
    except Exception as e:
        logger.error(f"❌ GCS: Failed to generate signed URL for {gcs_url}: {e}")
        return "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"

def generate_thumbnail_signed_url(gcs_url):
    """Generate a signed URL for a thumbnail."""
    # Thumbnails can have a longer expiry
    return generate_signed_url(gcs_url, duration_days=30)

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
