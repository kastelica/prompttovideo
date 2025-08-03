import os
import logging
import requests
import json
from flask import current_app

logger = logging.getLogger(__name__)

# Try to import Google Cloud libraries
try:
    import google.auth
    from google.auth.transport.requests import Request
    from google.cloud import storage
    GOOGLE_CLOUD_AVAILABLE = True
except ImportError:
    GOOGLE_CLOUD_AVAILABLE = False
    logger.warning("Google Cloud libraries not available. VeoClient will not be able to authenticate.")

class VeoClient:
    """Client for the Google Veo API, simplified for robust authentication."""
    
    def __init__(self):
        """Initialize VeoClient with project configuration."""
        self.project_id = os.environ.get('GOOGLE_CLOUD_PROJECT', 'dirly-466300')
        self.location = 'us-central1'
        self.model_id = 'veo-2.0-generate-001'  # Default model

    def _get_auth_token(self):
        """
        Gets a Google Cloud authentication token using Application Default Credentials.
        This is the standard and recommended way to authenticate.
        It works automatically in Cloud Run, GCE, and locally (via `gcloud auth application-default login`).
        """
        if not GOOGLE_CLOUD_AVAILABLE:
            logger.error("❌ VEO: Cannot get auth token because Google Cloud libraries are not installed.")
            return None

        try:
            # ===== START DEBUGGING =====
            logger.info("🕵️ VEO: Starting authentication process. Dumping all environment variables.")
            for key, value in os.environ.items():
                # Be careful not to log sensitive keys
                if 'KEY' in key.upper() or 'SECRET' in key.upper() or 'PASSWORD' in key.upper():
                    logger.info(f"  - ENV: {key}=**********")
                else:
                    logger.info(f"  - ENV: {key}={value}")
            
            gac = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            if gac:
                logger.warning(f"🚨 VEO: GOOGLE_APPLICATION_CREDENTIALS is SET to: {gac}")
                logger.warning("   This will override the default service account on Cloud Run.")
                logger.warning(f"   Checking if the file '{gac}' exists...")
                if os.path.exists(gac):
                    logger.info(f"   ✅ File '{gac}' exists.")
                else:
                    logger.error(f"   ❌ File '{gac}' DOES NOT exist. This is the likely cause of the error.")
                    # Unset the environment variable to fall back to default service account
                    logger.info("   🔄 Unsetting GOOGLE_APPLICATION_CREDENTIALS to use default service account")
                    if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
                        del os.environ['GOOGLE_APPLICATION_CREDENTIALS']
                    logger.info("   ✅ GOOGLE_APPLICATION_CREDENTIALS environment variable removed.")
            else:
                logger.info("✅ VEO: GOOGLE_APPLICATION_CREDENTIALS is NOT set. This is correct for Cloud Run.")
            # ===== END DEBUGGING =====

            logger.info("🔑 VEO: Getting token using Application Default Credentials (google.auth.default)")
            credentials, project = google.auth.default(
                scopes=[
                    'https://www.googleapis.com/auth/cloud-platform',
                    'https://www.googleapis.com/auth/aiplatform.googleapis.com'
                ]
            )
            
            # Refresh the token to ensure it's valid
            credentials.refresh(Request())
            
            if credentials.valid and credentials.token:
                logger.info("✅ VEO: Successfully obtained token using Application Default Credentials.")
                logger.info(f"🔍 VEO: Token preview: {str(credentials.token)[:20]}...")
                return credentials.token
            else:
                logger.error("❌ VEO: Application Default Credentials are not valid.")
                return None
                
        except Exception as e:
            logger.error(f"❌ VEO: Failed to get Application Default Credentials: {e}")
            import traceback
            logger.error(f"❌ VEO: Traceback: {traceback.format_exc()}")
            return None
    
    def generate_video(self, prompt, quality='free', duration=30):
        """Generate video using Veo API."""
        if quality == 'premium':
            self.model_id = 'veo-3.0-generate-001'
            max_duration = 60
            has_audio = True
        else:
            self.model_id = 'veo-2.0-generate-001'
            max_duration = 8
            has_audio = False

        logger.warning("💰 VEO: Real Veo API call will be made. This may incur costs.")
        
        token = self._get_auth_token()
        if not token:
            error_msg = "Failed to get a valid authentication token."
            logger.error(f"❌ VEO: {error_msg}")
            return {'success': False, 'error': error_msg}
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        request_data = {
            "instances": [{"prompt": prompt}],
            "parameters": {
                "durationSeconds": min(max(duration, 5), max_duration),
                "aspectRatio": "16:9",
                "enhancePrompt": True,
                "sampleCount": 1,
                "personGeneration": "allow_adult",
                "storageUri": f"gs://{get_gcs_bucket_name()}/videos/"
            }
        }
        
        if has_audio and quality == 'premium':
            request_data["parameters"]["generateAudio"] = True
        if quality == 'premium':
            request_data["parameters"]["resolution"] = "1080p"

        url = f"https://{self.location}-aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/{self.location}/publishers/google/models/{self.model_id}:predictLongRunning"
            
        try:
            response = requests.post(url, headers=headers, json=request_data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                operation_name = result.get('name')
                if operation_name:
                    logger.info(f"✅ VEO: Video generation started: {operation_name}")
                    return {'success': True, 'operation_name': operation_name}
                else:
                    logger.error(f"❌ VEO: No operation name in response: {result}")
                    return {'success': False, 'error': "No operation name in response"}
            else:
                error_msg = f"API request failed: {response.status_code} - {response.text}"
                logger.error(f"❌ VEO: {error_msg}")
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            logger.error(f"❌ VEO: Exception in generate_video: {e}")
            return {'success': False, 'error': str(e)}
    
    def check_video_status(self, operation_name):
        """Check the status of a video generation operation."""
        if 'veo-3.0' in operation_name:
            self.model_id = 'veo-3.0-generate-001'
        else:
            self.model_id = 'veo-2.0-generate-001'
        
        token = self._get_auth_token()
        if not token:
            error_msg = "Failed to get a valid authentication token for status check."
            logger.error(f"❌ VEO: {error_msg}")
            return {'success': False, 'error': error_msg}

        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        fetch_url = f"https://{self.location}-aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/{self.location}/publishers/google/models/{self.model_id}:fetchPredictOperation"
        request_data = {"operationName": operation_name}

        try:
            response = requests.post(fetch_url, headers=headers, json=request_data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"📡 VEO: Status check response: {result}")
                
                if result.get('done', False):
                    if 'error' in result:
                        error_msg = result['error'].get('message', 'Unknown error')
                        logger.error(f"❌ VEO: Operation failed: {error_msg}")
                        return {'success': False, 'status': 'failed', 'error': error_msg}
                    
                    if 'response' in result:
                        response_data = result['response']
                        
                        # Check for content policy violations
                        if 'raiMediaFilteredCount' in response_data and response_data['raiMediaFilteredCount'] > 0:
                            filtered_reasons = response_data.get('raiMediaFilteredReasons', [])
                            reason_text = filtered_reasons[0] if filtered_reasons else "Content policy violation"
                            logger.warning(f"🚫 VEO: Content policy violation detected: {reason_text}")
                            return {
                                'success': False, 
                                'status': 'content_violation', 
                                'error': 'Content policy violation',
                                'details': reason_text,
                                'filtered_count': response_data['raiMediaFilteredCount']
                            }
                        
                        if 'videos' in response_data and response_data['videos']:
                            video_data = response_data['videos'][0]
                            video_url = video_data.get('gcsUri')
                            if video_url:
                                return {'success': True, 'status': 'completed', 'video_url': video_url}
                    
                    # Fallback if structure is unexpected
                    logger.warning("Operation done but no video URL found in expected path. Trying fallback.")
                    operation_id = operation_name.split('/')[-1]
                    
                    # Try the standard Veo API folder structure first
                    expected_gcs_url = f"gs://{get_gcs_bucket_name()}/videos/{operation_id}/sample_0.mp4"
                    
                    if check_gcs_file_exists(expected_gcs_url):
                        logger.info(f"✅ Found video file in GCS via fallback: {expected_gcs_url}")
                        return {'success': True, 'status': 'completed', 'video_url': expected_gcs_url}
                    
                    # Try alternative path structure
                    expected_gcs_url_alt = f"gs://{get_gcs_bucket_name()}/videos/{operation_id}.mp4"
                    
                    if check_gcs_file_exists(expected_gcs_url_alt):
                        logger.info(f"✅ Found video file in GCS via alternative fallback: {expected_gcs_url_alt}")
                        return {'success': True, 'status': 'completed', 'video_url': expected_gcs_url_alt}

                    logger.error("❌ VEO: Operation complete but no video URL found.")
                    return {'success': False, 'status': 'failed', 'error': 'No video data in completed operation.'}
                else:
                    return {'success': True, 'status': 'processing'}
            else:
                error_msg = f"Status check failed: {response.status_code} - {response.text}"
                logger.error(f"❌ VEO: {error_msg}")
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            logger.error(f"❌ VEO: Error checking video status: {e}")
            return {'success': False, 'error': str(e)}

def get_gcs_bucket_name():
    """Helper to get GCS bucket name, avoiding circular import with gcs_utils."""
    return os.environ.get('GCS_BUCKET_NAME', 'prompt-veo-videos')

def check_gcs_file_exists(gcs_url):
    """Helper to check if a file exists in GCS, avoiding circular import."""
    if not GOOGLE_CLOUD_AVAILABLE:
        return False
    try:
        storage_client = storage.Client()
        bucket_name = gcs_url.split('/')[2]
        blob_name = '/'.join(gcs_url.split('/')[3:])
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        return blob.exists()
    except Exception as e:
        logger.error(f"❌ GCS: Error checking if file exists '{gcs_url}': {e}")
        return False
