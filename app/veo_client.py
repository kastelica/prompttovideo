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
            logger.info("🕵️ VEO: Starting authentication process.")
            
            # Check if we're in Cloud Run environment
            is_cloud_run = os.environ.get('K_SERVICE') is not None
            logger.info(f"🌐 Environment: {'Cloud Run' if is_cloud_run else 'Local/Other'}")
            
            gac = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            if gac:
                logger.warning(f"🚨 VEO: GOOGLE_APPLICATION_CREDENTIALS is SET to: {gac}")
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

            # Try different authentication methods
            credentials = None
            
            # Method 1: Try Application Default Credentials (but don't refresh yet)
            try:
                logger.info("🔑 VEO: Method 1 - Trying google.auth.default...")
                credentials, project = google.auth.default(
                    scopes=[
                        'https://www.googleapis.com/auth/cloud-platform',
                        'https://www.googleapis.com/auth/aiplatform.googleapis.com'
                    ]
                )
                logger.info(f"✅ VEO: Successfully obtained credentials using google.auth.default (type: {type(credentials).__name__})")
                
                # Try to refresh the token
                try:
                    logger.info("🔄 VEO: Attempting to refresh credentials...")
                    credentials.refresh(Request())
                    logger.info("✅ VEO: Successfully refreshed credentials")
                except Exception as refresh_error:
                    logger.warning(f"⚠️ VEO: Credential refresh failed: {refresh_error}")
                    logger.info("🔄 VEO: Trying alternative authentication methods...")
                    credentials = None  # Reset to try fallback methods
                    
            except Exception as e:
                logger.warning(f"⚠️ VEO: google.auth.default failed: {e}")
                credentials = None
            
            # Method 2: Try Compute Engine credentials (for Cloud Run)
            if not credentials and is_cloud_run:
                try:
                    logger.info("🔑 VEO: Method 2 - Trying Compute Engine credentials...")
                    from google.auth.compute_engine import Credentials
                    credentials = Credentials()
                    logger.info("✅ VEO: Successfully obtained credentials using Compute Engine credentials")
                    
                    # Try to refresh
                    try:
                        credentials.refresh(Request())
                        logger.info("✅ VEO: Successfully refreshed Compute Engine credentials")
                    except Exception as refresh_error:
                        logger.warning(f"⚠️ VEO: Compute Engine credential refresh failed: {refresh_error}")
                        
                except Exception as e2:
                    logger.warning(f"⚠️ VEO: Compute Engine credentials failed: {e2}")
                    credentials = None
            
            # Method 3: Try service account credentials
            if not credentials:
                try:
                    logger.info("🔑 VEO: Method 3 - Trying service account credentials...")
                    from google.oauth2 import service_account
                    # Try to use the default service account
                    credentials = service_account.Credentials.from_service_account_info(
                        {},  # Empty dict to use default
                        scopes=[
                            'https://www.googleapis.com/auth/cloud-platform',
                            'https://www.googleapis.com/auth/aiplatform.googleapis.com'
                        ]
                    )
                    logger.info("✅ VEO: Successfully obtained credentials using service account")
                    
                    # Try to refresh
                    try:
                        credentials.refresh(Request())
                        logger.info("✅ VEO: Successfully refreshed service account credentials")
                    except Exception as refresh_error:
                        logger.warning(f"⚠️ VEO: Service account credential refresh failed: {refresh_error}")
                        
                except Exception as e3:
                    logger.error(f"❌ VEO: Service account credentials failed: {e3}")
                    credentials = None
            
            # Method 4: Try direct metadata server access (last resort)
            if not credentials and is_cloud_run:
                try:
                    logger.info("🔑 VEO: Method 4 - Trying direct metadata server access...")
                    import requests
                    
                    # Try to get token directly from metadata server
                    metadata_url = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
                    headers = {"Metadata-Flavor": "Google"}
                    params = {
                        "scopes": "https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/aiplatform.googleapis.com"
                    }
                    
                    response = requests.get(metadata_url, headers=headers, params=params, timeout=10)
                    if response.status_code == 200:
                        token_data = response.json()
                        token = token_data.get('access_token')
                        if token:
                            logger.info("✅ VEO: Successfully obtained token directly from metadata server")
                            return token
                        else:
                            logger.warning("⚠️ VEO: No access_token in metadata response")
                    else:
                        logger.warning(f"⚠️ VEO: Metadata server returned {response.status_code}")
                        
                except Exception as e4:
                    logger.warning(f"⚠️ VEO: Direct metadata access failed: {e4}")
            
            if not credentials:
                logger.error("❌ VEO: No credentials obtained from any method")
                return None
            
            # Check if we have a valid token
            if credentials.valid and credentials.token:
                logger.info("✅ VEO: Successfully obtained valid token.")
                logger.info(f"🔍 VEO: Token preview: {str(credentials.token)[:20]}...")
                return credentials.token
            else:
                logger.error("❌ VEO: Credentials are not valid or have no token.")
                logger.error(f"🔍 VEO: Credentials valid: {credentials.valid if credentials else 'None'}")
                logger.error(f"🔍 VEO: Has token: {bool(credentials.token) if credentials else 'None'}")
                return None
                
        except Exception as e:
            logger.error(f"❌ VEO: Failed to get authentication token: {e}")
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

    def generate_image_to_video(self, instances, parameters):
        """Generate video from image using Veo API."""
        logger.warning("💰 VEO: Real Veo image-to-video API call will be made. This may incur costs.")
        
        token = self._get_auth_token()
        if not token:
            error_msg = "Failed to get a valid authentication token."
            logger.error(f"❌ VEO: {error_msg}")
            return None
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        request_data = {
            "instances": instances,
            "parameters": parameters
        }
        
        # Add storage URI if not provided
        if 'storageUri' not in parameters:
            request_data["parameters"]["storageUri"] = f"gs://{get_gcs_bucket_name()}/videos/"

        url = f"https://{self.location}-aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/{self.location}/publishers/google/models/{self.model_id}:predictLongRunning"
            
        try:
            logger.info(f"🎬 VEO: Sending image-to-video request to: {url}")
            logger.info(f"📦 VEO: Request data: {request_data}")
            
            response = requests.post(url, headers=headers, json=request_data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                operation_name = result.get('name')
                if operation_name:
                    logger.info(f"✅ VEO: Image-to-video generation started: {operation_name}")
                    return operation_name
                else:
                    logger.error(f"❌ VEO: No operation name in response: {result}")
                    return None
            else:
                error_msg = f"API request failed: {response.status_code} - {response.text}"
                logger.error(f"❌ VEO: {error_msg}")
                return None
                
        except Exception as e:
            logger.error(f"❌ VEO: Exception in generate_image_to_video: {e}")
            return None

    def check_image_to_video_status(self, operation_name):
        """Check the status of an image-to-video generation operation."""
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
                logger.info(f"📡 VEO: Image-to-video status check response: {result}")
                
                if result.get('done', False):
                    if 'error' in result:
                        error_msg = result['error'].get('message', 'Unknown error')
                        logger.error(f"❌ VEO: Image-to-video operation failed: {error_msg}")
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
                        
                        # Handle video results
                        if 'videos' in response_data and response_data['videos']:
                            videos = []
                            for i, video_data in enumerate(response_data['videos']):
                                video_url = video_data.get('gcsUri')
                                if video_url:
                                    # Convert GCS URL to signed URL for direct access
                                    try:
                                        from app.gcs_utils import generate_signed_url
                                        signed_url = generate_signed_url(video_url, duration_days=1)  # 1 day
                                        videos.append({
                                            'index': i,
                                            'url': signed_url,
                                            'gcs_uri': video_url
                                        })
                                    except Exception as url_error:
                                        logger.warning(f"⚠️ VEO: Could not generate signed URL for {video_url}: {url_error}")
                                        videos.append({
                                            'index': i,
                                            'url': video_url,
                                            'gcs_uri': video_url
                                        })
                            
                            if videos:
                                return {
                                    'success': True, 
                                    'status': 'completed', 
                                    'done': True,
                                    'videos': videos
                                }
                    
                    # Fallback if structure is unexpected
                    logger.warning("Image-to-video operation done but no video URLs found in expected path. Trying fallback.")
                    operation_id = operation_name.split('/')[-1]
                    
                    # Try the standard Veo API folder structure
                    videos = []
                    for i in range(4):  # Try up to 4 videos
                        expected_gcs_url = f"gs://{get_gcs_bucket_name()}/videos/{operation_id}/sample_{i}.mp4"
                        
                        if check_gcs_file_exists(expected_gcs_url):
                            try:
                                from app.gcs_utils import generate_signed_url
                                signed_url = generate_signed_url(expected_gcs_url, duration_days=1)
                                videos.append({
                                    'index': i,
                                    'url': signed_url,
                                    'gcs_uri': expected_gcs_url
                                })
                            except Exception as url_error:
                                logger.warning(f"⚠️ VEO: Could not generate signed URL for {expected_gcs_url}: {url_error}")
                                videos.append({
                                    'index': i,
                                    'url': expected_gcs_url,
                                    'gcs_uri': expected_gcs_url
                                })
                    
                    if videos:
                        logger.info(f"✅ Found {len(videos)} video files in GCS via fallback")
                        return {
                            'success': True, 
                            'status': 'completed', 
                            'done': True,
                            'videos': videos
                        }

                    logger.error("❌ VEO: Image-to-video operation complete but no video URLs found.")
                    return {'success': False, 'status': 'failed', 'error': 'No video data in completed operation.'}
                else:
                    return {'success': True, 'status': 'processing', 'done': False}
            else:
                error_msg = f"Status check failed: {response.status_code} - {response.text}"
                logger.error(f"❌ VEO: {error_msg}")
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            logger.error(f"❌ VEO: Error checking image-to-video status: {e}")
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
