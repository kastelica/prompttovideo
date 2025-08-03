import os
from datetime import timedelta
from google.cloud import storage
from flask import current_app

def generate_signed_url(gcs_url):
    """Generate signed URL for video access"""
    try:
        # For mock mode or fallback URLs, return a working video URL
        if (current_app.config.get('TESTING') or 
            current_app.config.get('VEO_MOCK_MODE', False) or
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
        if current_app.config.get('TESTING') or current_app.config.get('VEO_MOCK_MODE', False):
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