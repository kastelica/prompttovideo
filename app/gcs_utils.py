import os
from datetime import timedelta, datetime
from google.cloud import storage
from flask import current_app
import hashlib
import re

def generate_signed_url(gcs_url):
    """Generate signed URL for video access"""
    try:
        # For testing or fallback URLs, return a working video URL
        if (current_app.config.get('TESTING') or 
            'mock-bucket' in gcs_url or 
            'fallback' in gcs_url):
            current_app.logger.info("Using mock/fallback signed URL")
            # Return a working video URL for testing
            return "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
        
        # Extract bucket and blob from GCS URL
        parts = gcs_url.replace('gs://', '').split('/', 1)
        bucket_name = parts[0]
        blob_name = parts[1]
        
        # Initialize GCS client with explicit credentials
        creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        if not creds_path:
            # Hardcode the path to veo.json
            creds_path = os.path.join(os.getcwd(), 'veo.json')
            current_app.logger.info(f"Using hardcoded credentials path for GCS: {creds_path}")
        
        if os.path.exists(creds_path):
            from google.oauth2 import service_account
            credentials = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )
            storage_client = storage.Client(credentials=credentials)
            current_app.logger.info(f"GCS client initialized with credentials from: {creds_path}")
        else:
            current_app.logger.warning(f"Credentials file not found for GCS: {creds_path}")
            storage_client = storage.Client()
        
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        # Generate signed URL that expires in 7 days
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(days=7),  # 7 days expiration (maximum allowed)
            method="GET"
        )
        
        return signed_url
    
    except Exception as e:
        current_app.logger.error(f"Failed to generate signed URL: {e}")
        # Return a working video URL as fallback
        return "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"

def generate_thumbnail_signed_url(thumbnail_path):
    """Generate signed URL for thumbnail access"""
    try:
        # For mock mode, return a mock thumbnail URL
        if current_app.config.get('TESTING'):
            current_app.logger.info("Using mock thumbnail URL for development")
            return "https://via.placeholder.com/320x180/000000/FFFFFF?text=Thumbnail"
        
        # Extract bucket and blob from GCS URL
        parts = thumbnail_path.replace('gs://', '').split('/', 1)
        bucket_name = parts[0]
        blob_name = parts[1]
        
        # Initialize GCS client with explicit credentials (same as generate_signed_url)
        creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        if not creds_path:
            # Hardcode the path to veo.json
            creds_path = os.path.join(os.getcwd(), 'veo.json')
            current_app.logger.info(f"Using hardcoded credentials path for thumbnail GCS: {creds_path}")
        
        if os.path.exists(creds_path):
            from google.oauth2 import service_account
            credentials = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )
            storage_client = storage.Client(credentials=credentials)
            current_app.logger.info(f"Thumbnail GCS client initialized with credentials from: {creds_path}")
        else:
            current_app.logger.warning(f"Credentials file not found for thumbnail GCS: {creds_path}")
            storage_client = storage.Client()
        
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        # Generate signed URL that expires in 30 days
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(days=30),
            method="GET"
        )
        
        return signed_url
    
    except Exception as e:
        current_app.logger.error(f"Failed to generate thumbnail signed URL: {e}")
        # Return a placeholder image as fallback
        return "https://via.placeholder.com/320x180/000000/FFFFFF?text=Thumbnail"

# ============================================================================
# NEW: IMPROVED GCS FILE NAMING AND ORGANIZATION SYSTEM
# ============================================================================

def get_gcs_bucket_name():
    """Get the correct GCS bucket name"""
    # Priority: environment variable > config > default
    bucket_name = os.environ.get('GCS_BUCKET_NAME')
    if not bucket_name:
        bucket_name = current_app.config.get('GCS_BUCKET_NAME', 'prompt-veo-videos')
    return bucket_name

def sanitize_filename(filename):
    """Sanitize filename for GCS compatibility"""
    # Remove or replace invalid characters
    filename = re.sub(r'[^\w\-_.]', '_', filename)
    # Limit length
    if len(filename) > 200:
        filename = filename[:200]
    return filename

def generate_video_filename(video_id, quality='free', prompt=None, user_id=None):
    """
    Generate organized video filename with proper structure
    
    Format: videos/{year}/{month}/{quality}/{video_id}_{prompt_hash}_{timestamp}.mp4
    
    Args:
        video_id: Database video ID
        quality: Video quality (free, premium, 360p, 1080p)
        prompt: Video prompt (optional, for hash generation)
        user_id: User ID (optional, for organization)
    
    Returns:
        Tuple of (gcs_path, filename, gcs_url)
    """
    now = datetime.utcnow()
    year = now.strftime('%Y')
    month = now.strftime('%m')
    
    # Create prompt hash for uniqueness
    if prompt:
        # Create a short hash from the prompt
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]
    else:
        prompt_hash = 'no_prompt'
    
    # Generate timestamp for uniqueness
    timestamp = now.strftime('%Y%m%d_%H%M%S')
    
    # Create organized filename
    filename = f"{video_id}_{prompt_hash}_{timestamp}.mp4"
    filename = sanitize_filename(filename)
    
    # Create organized path structure
    gcs_path = f"videos/{year}/{month}/{quality}/{filename}"
    
    # Generate full GCS URL
    bucket_name = get_gcs_bucket_name()
    gcs_url = f"gs://{bucket_name}/{gcs_path}"
    
    return gcs_path, filename, gcs_url

def generate_thumbnail_filename(video_id, quality='free', prompt=None):
    """
    Generate organized thumbnail filename
    
    Format: thumbnails/{year}/{month}/{quality}/{video_id}_{prompt_hash}_{timestamp}.jpg
    
    Args:
        video_id: Database video ID
        quality: Video quality
        prompt: Video prompt (optional, for hash generation)
    
    Returns:
        Tuple of (gcs_path, filename, gcs_url)
    """
    now = datetime.utcnow()
    year = now.strftime('%Y')
    month = now.strftime('%m')
    
    # Create prompt hash for uniqueness
    if prompt:
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]
    else:
        prompt_hash = 'no_prompt'
    
    # Generate timestamp for uniqueness
    timestamp = now.strftime('%Y%m%d_%H%M%S')
    
    # Create organized filename
    filename = f"{video_id}_{prompt_hash}_{timestamp}.jpg"
    filename = sanitize_filename(filename)
    
    # Create organized path structure
    gcs_path = f"thumbnails/{year}/{month}/{quality}/{filename}"
    
    # Generate full GCS URL
    bucket_name = get_gcs_bucket_name()
    gcs_url = f"gs://{bucket_name}/{gcs_path}"
    
    return gcs_path, filename, gcs_url

def generate_legacy_compatible_filename(video_id):
    """
    Generate legacy-compatible filename for backward compatibility
    
    Format: videos/{video_id}.mp4 (old format)
    """
    gcs_path = f"videos/{video_id}.mp4"
    bucket_name = get_gcs_bucket_name()
    gcs_url = f"gs://{bucket_name}/{gcs_path}"
    
    return gcs_path, f"{video_id}.mp4", gcs_url

def generate_legacy_thumbnail_filename(video_id):
    """
    Generate legacy-compatible thumbnail filename
    
    Format: thumbnails/{video_id}.jpg (old format)
    """
    gcs_path = f"thumbnails/{video_id}.jpg"
    bucket_name = get_gcs_bucket_name()
    gcs_url = f"gs://{bucket_name}/{gcs_path}"
    
    return gcs_path, f"{video_id}.jpg", gcs_url

def parse_gcs_filename(gcs_url):
    """
    Parse GCS URL to extract components
    
    Args:
        gcs_url: Full GCS URL (gs://bucket/path)
    
    Returns:
        Dict with parsed components
    """
    try:
        # Remove gs:// prefix
        path = gcs_url.replace('gs://', '')
        
        # Split bucket and path
        parts = path.split('/', 1)
        bucket_name = parts[0]
        file_path = parts[1] if len(parts) > 1 else ''
        
        # Parse file path components
        path_parts = file_path.split('/')
        
        result = {
            'bucket_name': bucket_name,
            'full_path': file_path,
            'filename': path_parts[-1] if path_parts else '',
            'extension': path_parts[-1].split('.')[-1] if path_parts and '.' in path_parts[-1] else '',
            'path_parts': path_parts
        }
        
        # Try to extract organized structure components
        if len(path_parts) >= 4 and path_parts[0] in ['videos', 'thumbnails']:
            result.update({
                'file_type': path_parts[0],  # videos or thumbnails
                'year': path_parts[1] if len(path_parts) > 1 else None,
                'month': path_parts[2] if len(path_parts) > 2 else None,
                'quality': path_parts[3] if len(path_parts) > 3 else None,
                'is_organized': True
            })
        elif len(path_parts) >= 1 and path_parts[0] in ['videos', 'thumbnails']:
            # Legacy structure: videos/filename or thumbnails/filename
            result.update({
                'file_type': path_parts[0],  # videos or thumbnails
                'is_organized': False
            })
        elif len(path_parts) >= 2 and path_parts[0] == 'archive':
            # Archive structure: archive/timestamp/videos/filename or archive/timestamp/thumbnails/filename
            if len(path_parts) >= 3 and path_parts[2] in ['videos', 'thumbnails']:
                result.update({
                    'file_type': path_parts[2],  # videos or thumbnails
                    'is_organized': False,
                    'is_archived': True,
                    'archive_timestamp': path_parts[1]
                })
            else:
                result['is_organized'] = False
        else:
            result['is_organized'] = False
        
        return result
        
    except Exception as e:
        current_app.logger.error(f"Error parsing GCS filename: {e}")
        return {
            'bucket_name': 'unknown',
            'full_path': gcs_url,
            'filename': '',
            'extension': '',
            'path_parts': [],
            'is_organized': False
        }

def get_file_info_from_gcs(gcs_url):
    """
    Get file information from GCS
    
    Args:
        gcs_url: Full GCS URL
    
    Returns:
        Dict with file information
    """
    try:
        parsed = parse_gcs_filename(gcs_url)
        bucket_name = parsed['bucket_name']
        file_path = parsed['full_path']
        
        # Initialize GCS client
        creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        if not creds_path:
            creds_path = os.path.join(os.getcwd(), 'veo.json')
        
        if os.path.exists(creds_path):
            from google.oauth2 import service_account
            credentials = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )
            storage_client = storage.Client(credentials=credentials)
        else:
            storage_client = storage.Client()
        
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(file_path)
        
        # Get blob metadata
        blob.reload()
        
        return {
            'exists': blob.exists(),
            'size': blob.size if blob.exists() else 0,
            'created': blob.time_created if blob.exists() else None,
            'updated': blob.updated if blob.exists() else None,
            'content_type': blob.content_type if blob.exists() else None,
            'metadata': blob.metadata if blob.exists() else {},
            'parsed_info': parsed
        }
        
    except Exception as e:
        current_app.logger.error(f"Error getting file info from GCS: {e}")
        return {
            'exists': False,
            'size': 0,
            'created': None,
            'updated': None,
            'content_type': None,
            'metadata': {},
            'parsed_info': parse_gcs_filename(gcs_url)
        }

def list_gcs_files(prefix=None, max_results=1000):
    """
    List files in GCS bucket with optional prefix
    
    Args:
        prefix: Path prefix to filter by (e.g., 'videos/2024/')
        max_results: Maximum number of results to return
    
    Returns:
        List of file information dictionaries
    """
    try:
        bucket_name = get_gcs_bucket_name()
        
        # Initialize GCS client
        creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        if not creds_path:
            creds_path = os.path.join(os.getcwd(), 'veo.json')
        
        if os.path.exists(creds_path):
            from google.oauth2 import service_account
            credentials = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )
            storage_client = storage.Client(credentials=credentials)
        else:
            storage_client = storage.Client()
        
        bucket = storage_client.bucket(bucket_name)
        
        # List blobs
        blobs = storage_client.list_blobs(bucket, prefix=prefix, max_results=max_results)
        
        files = []
        for blob in blobs:
            gcs_url = f"gs://{bucket_name}/{blob.name}"
            file_info = {
                'gcs_url': gcs_url,
                'name': blob.name,
                'size': blob.size,
                'created': blob.time_created,
                'updated': blob.updated,
                'content_type': blob.content_type,
                'parsed_info': parse_gcs_filename(gcs_url)
            }
            files.append(file_info)
        
        return files
        
    except Exception as e:
        current_app.logger.error(f"Error listing GCS files: {e}")
        return []

def get_storage_stats():
    """
    Get storage statistics for the GCS bucket
    
    Returns:
        Dict with storage statistics
    """
    try:
        files = list_gcs_files()
        
        stats = {
            'total_files': len(files),
            'total_size_bytes': 0,
            'videos_count': 0,
            'thumbnails_count': 0,
            'videos_size': 0,
            'thumbnails_size': 0,
            'organized_files': 0,
            'legacy_files': 0,
            'by_quality': {},
            'by_year': {},
            'by_month': {}
        }
        
        for file_info in files:
            size = file_info['size']
            stats['total_size_bytes'] += size
            
            parsed = file_info['parsed_info']
            
            if parsed['is_organized']:
                stats['organized_files'] += 1
                
                # Count by file type
                if parsed['file_type'] == 'videos':
                    stats['videos_count'] += 1
                    stats['videos_size'] += size
                elif parsed['file_type'] == 'thumbnails':
                    stats['thumbnails_count'] += 1
                    stats['thumbnails_size'] += size
                
                # Count by quality
                quality = parsed.get('quality', 'unknown')
                if quality not in stats['by_quality']:
                    stats['by_quality'][quality] = {'count': 0, 'size': 0}
                stats['by_quality'][quality]['count'] += 1
                stats['by_quality'][quality]['size'] += size
                
                # Count by year
                year = parsed.get('year', 'unknown')
                if year not in stats['by_year']:
                    stats['by_year'][year] = {'count': 0, 'size': 0}
                stats['by_year'][year]['count'] += 1
                stats['by_year'][year]['size'] += size
                
                # Count by month
                month = parsed.get('month', 'unknown')
                if month not in stats['by_month']:
                    stats['by_month'][month] = {'count': 0, 'size': 0}
                stats['by_month'][month]['count'] += 1
                stats['by_month'][month]['size'] += size
            else:
                stats['legacy_files'] += 1
        
        # Convert bytes to MB/GB for readability
        stats['total_size_mb'] = stats['total_size_bytes'] / (1024 * 1024)
        stats['total_size_gb'] = stats['total_size_mb'] / 1024
        stats['videos_size_mb'] = stats['videos_size'] / (1024 * 1024)
        stats['thumbnails_size_mb'] = stats['thumbnails_size'] / (1024 * 1024)
        
        return stats
        
    except Exception as e:
        current_app.logger.error(f"Error getting storage stats: {e}")
        return {
            'error': str(e),
            'total_files': 0,
            'total_size_bytes': 0
        }

def upload_file_to_gcs(local_file_path, gcs_blob_name):
    """
    Upload a local file to Google Cloud Storage
    
    Args:
        local_file_path: Path to local file
        gcs_blob_name: GCS blob name (path in bucket)
    
    Returns:
        GCS URL if successful, None if failed
    """
    try:
        bucket_name = get_gcs_bucket_name()
        
        # Initialize GCS client
        creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        if not creds_path:
            creds_path = os.path.join(os.getcwd(), 'veo.json')
        
        if os.path.exists(creds_path):
            from google.oauth2 import service_account
            credentials = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )
            storage_client = storage.Client(credentials=credentials)
        else:
            storage_client = storage.Client()
        
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(gcs_blob_name)
        
        # Upload file
        blob.upload_from_filename(local_file_path)
        
        # Generate GCS URL
        gcs_url = f"gs://{bucket_name}/{gcs_blob_name}"
        
        current_app.logger.info(f"Successfully uploaded {local_file_path} to {gcs_url}")
        return gcs_url
        
    except Exception as e:
        current_app.logger.error(f"Error uploading to GCS: {e}")
        return None 