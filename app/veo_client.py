import os
import logging
import requests
import json
from datetime import datetime
from flask import current_app

logger = logging.getLogger(__name__)

# Try to import Google Cloud libraries
try:
    from google.oauth2 import service_account
    from google.auth.transport import requests as google_requests
    GOOGLE_CLOUD_AVAILABLE = True
except ImportError:
    GOOGLE_CLOUD_AVAILABLE = False
    current_app.logger.warning("Google Cloud libraries not available - VeoClient will use mock mode")

class VeoClient:
    """Client for Google Veo API"""
    
    def __init__(self):
        """Initialize VeoClient with project configuration"""
        self.project_id = os.environ.get('GOOGLE_CLOUD_PROJECT_ID', 'dirly-466300')
        self.location = 'us-central1'
        # Default to Veo 2, will be updated based on quality in generate_video method
        self.model_id = 'veo-2.0-generate-001'
        self.credentials = None
        
        # If Google Cloud libraries are not available, skip credential initialization
        if not GOOGLE_CLOUD_AVAILABLE:
            current_app.logger.warning("Google Cloud libraries not available - VeoClient will use mock mode")
            return
        
        # Hardcode the credentials path for the web server
        creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        if not creds_path:
            # Hardcode the path to veo.json
            creds_path = os.path.join(os.getcwd(), 'veo.json')
            current_app.logger.info(f"Using hardcoded credentials path: {creds_path}")
        
        if os.path.exists(creds_path):
            self._init_google_auth(creds_path)
        else:
            current_app.logger.warning(f"Credentials file not found: {creds_path}")
            current_app.logger.warning("VeoClient will use default credentials")
            self._init_google_auth()
    
    def _init_google_auth(self, creds_path=None):
        """Initialize Google Cloud authentication"""
        try:
            if creds_path and os.path.exists(creds_path):
                # Use service account credentials
                self.credentials = service_account.Credentials.from_service_account_file(
                    creds_path,
                    scopes=['https://www.googleapis.com/auth/cloud-platform']
                )
                logger.info(f"Google Cloud authentication initialized with service account: {creds_path}")
            else:
                # Use default credentials (for Cloud Run)
                self.credentials = None
                logger.info("Google Cloud authentication initialized with default credentials")
            
        except Exception as e:
            logger.error(f"DEBUG: Google Cloud authentication failed with exception: {e}")
            logger.warning(f"Google Cloud authentication failed: {e}")
            logger.info("You may need to set up Google Cloud credentials")
            self.credentials = None
    
    def _get_auth_token(self):
        """Get authentication token for Google Cloud API"""
        try:
            # If Google Cloud libraries are not available, return mock token
            if not GOOGLE_CLOUD_AVAILABLE:
                current_app.logger.warning("Google Cloud libraries not available, using mock token")
                return "mock_token_for_development"
            
            # Hardcode the credentials path for the web server
            creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            if not creds_path:
                # Hardcode the path to veo.json
                creds_path = os.path.join(os.getcwd(), 'veo.json')
                current_app.logger.info(f"Using hardcoded credentials path: {creds_path}")
            
            if not os.path.exists(creds_path):
                current_app.logger.error(f"Credentials file not found: {creds_path}")
                return "mock_token_for_development"
            
            # Load credentials from the hardcoded path
            credentials = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )
            
            # Get the token using Google requests
            auth_req = google_requests.Request()
            credentials.refresh(auth_req)
            
            if credentials.valid:
                current_app.logger.info(f"Loaded Google Cloud credentials from: {creds_path}")
                return credentials.token
            else:
                current_app.logger.error("Credentials not valid after refresh")
                return "mock_token_for_development"
                
        except Exception as e:
            current_app.logger.error(f"Google Cloud authentication failed: {e}")
            current_app.logger.error(f"DEBUG: GOOGLE_APPLICATION_CREDENTIALS environment variable not set")
            return "mock_token_for_development"
    
    def generate_video(self, prompt, quality='free', duration=30):
        """Generate video using Veo API"""
        
        # Set model based on quality
        if quality == 'premium':
            self.model_id = 'veo-3.0-generate-001'
            max_duration = 60
            has_audio = True
        else:
            self.model_id = 'veo-2.0-generate-001'
            max_duration = 8
            has_audio = False
        
        current_app.logger.info(f"🎯 VEO: Has audio: {has_audio}")
        
        try:
            # ⚠️ COST WARNING: Real Veo API calls will charge you money
            current_app.logger.warning("💰 VEO: WARNING - Real Veo API calls will charge your Google Cloud account")
            current_app.logger.warning("💰 VEO: Each video generation costs money, even if it fails")
            
            current_app.logger.info("🌐 VEO: Using real Veo API")
            
            # Use real Veo API
            current_app.logger.info("🔑 VEO: Getting authentication token")
            token = self._get_auth_token()
            if not token:
                current_app.logger.error("❌ VEO: Failed to get authentication token")
                raise Exception("Failed to get authentication token")
            
            current_app.logger.info("✅ VEO: Authentication token obtained")
            
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            current_app.logger.info(f"📋 VEO: Headers prepared: {headers}")
            
            # Prepare request data according to Veo API documentation
            request_data = {
                "instances": [
                    {
                        "prompt": prompt
                    }
                ],
                "parameters": {
                    "durationSeconds": min(max(duration, 5), max_duration),
                    "aspectRatio": "16:9",
                    "enhancePrompt": True,
                    "sampleCount": 1,
                    "personGeneration": "allow_adult",
                    "storageUri": f"gs://prompt-veo-videos/videos/"
                }
            }
            
            # Add audio generation for premium (Veo 3) - only Veo 3 supports audio
            if has_audio and quality == 'premium':
                request_data["parameters"]["generateAudio"] = True
                current_app.logger.info("🎵 VEO: Audio generation enabled for premium video")
            else:
                current_app.logger.info("🔇 VEO: Audio generation disabled (free tier or Veo 2)")
            
            # Add resolution for Veo 3 models
            if quality == 'premium':
                request_data["parameters"]["resolution"] = "1080p"
                current_app.logger.info("📺 VEO: 1080p resolution enabled for premium video")
            
            current_app.logger.info(f"📤 VEO: Request data prepared: {request_data}")
            current_app.logger.info(f"📤 VEO: Model: {self.model_id}")
            current_app.logger.info(f"📤 VEO: Duration: {min(max(duration, 5), max_duration)} seconds")
            current_app.logger.info(f"📤 VEO: Audio generation: {has_audio}")
            
            # Add detailed logging for the request
            current_app.logger.info(f"=== VEO: VIDEO GENERATION REQUEST DEBUG ===")
            current_app.logger.info(f"VEO: Prompt: '{prompt}'")
            current_app.logger.info(f"VEO: Quality: {quality}")
            current_app.logger.info(f"VEO: Duration: {min(max(duration, 5), max_duration)} seconds")
            current_app.logger.info(f"VEO: Model: {self.model_id}")
            current_app.logger.info(f"VEO: Request data: {request_data}")
            current_app.logger.info(f"VEO: Headers: {headers}")
            current_app.logger.info(f"=== VEO: END REQUEST DEBUG ===")
            
            # Make the API request
            url = f"https://{self.location}-aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/{self.location}/publishers/google/models/{self.model_id}:predictLongRunning"
            
            current_app.logger.info(f"🌐 VEO: API URL: {url}")
            current_app.logger.info(f"🌐 VEO: About to make POST request to Veo API")
            current_app.logger.info(f"🌐 VEO: Request timeout: 30 seconds")
            
            response = requests.post(url, headers=headers, json=request_data, timeout=30)
            
            current_app.logger.info(f"📡 VEO: Response received")
            current_app.logger.info(f"📡 VEO: Response status code: {response.status_code}")
            current_app.logger.info(f"📡 VEO: Response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                current_app.logger.info(f"✅ VEO: API request successful (200)")
                result = response.json()
                
                # Add detailed logging for the response
                current_app.logger.info(f"=== VEO: VIDEO GENERATION RESPONSE DEBUG ===")
                current_app.logger.info(f"VEO: Response status code: {response.status_code}")
                current_app.logger.info(f"VEO: Response headers: {dict(response.headers)}")
                current_app.logger.info(f"VEO: Response text length: {len(response.text)}")
                current_app.logger.info(f"VEO: Response text preview: {response.text[:500]}...")
                current_app.logger.info(f"VEO: Parsed result: {result}")
                current_app.logger.info(f"VEO: Result type: {type(result)}")
                if isinstance(result, dict):
                    current_app.logger.info(f"VEO: All result keys: {list(result.keys())}")
                    for key, value in result.items():
                        current_app.logger.info(f"VEO: Key '{key}': {type(value)} = {value}")
                current_app.logger.info(f"=== VEO: END RESPONSE DEBUG ===")
                
                operation_name = result.get('name')
                current_app.logger.info(f"🎯 VEO: Operation name extracted: {operation_name}")
                
                if operation_name:
                    current_app.logger.info(f"✅ VEO: Video generation operation started successfully")
                    current_app.logger.info(f"🌐 VEO: ===== VEO API: GENERATE VIDEO COMPLETED =====")
                    return {
                        'success': True,
                        'operation_name': operation_name
                    }
                else:
                    current_app.logger.error(f"❌ VEO: No operation name in response")
                    current_app.logger.error(f"❌ VEO: Full response: {result}")
                    current_app.logger.info(f"🌐 VEO: ===== VEO API: GENERATE VIDEO FAILED =====")
                    raise Exception("No operation name in response")
            else:
                error_msg = f"API request failed: {response.status_code} - {response.text}"
                current_app.logger.error(f"❌ VEO: {error_msg}")
                current_app.logger.info(f"🌐 VEO: ===== VEO API: GENERATE VIDEO FAILED =====")
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            current_app.logger.error(f"❌ VEO: Exception in generate_video: {e}")
            current_app.logger.error(f"❌ VEO: Exception type: {type(e)}")
            import traceback
            current_app.logger.error(f"❌ VEO: Exception traceback: {traceback.format_exc()}")
            current_app.logger.info(f"🌐 VEO: ===== VEO API: GENERATE VIDEO EXCEPTION =====")
            return {'success': False, 'error': str(e)}
    
    def check_video_status(self, operation_name):
        """Check the status of a video generation operation (Veo 3 API)"""
        current_app.logger.info(f"🔍 VEO: ===== VEO API: CHECK STATUS STARTED =====")
        current_app.logger.info(f"🔍 VEO: Operation name: {operation_name}")
        current_app.logger.info(f"🔍 VEO: Operation name type: {type(operation_name)}")
        
        # Determine the model from the operation name
        if 'veo-3.0' in operation_name:
            self.model_id = 'veo-3.0-generate-001'
        else:
            self.model_id = 'veo-2.0-generate-001'
        
        current_app.logger.info(f"🔍 VEO: Using model: {self.model_id}")
        
        try:
            current_app.logger.info("🌐 VEO: Using real Veo API for status check")
            
            # Use real Veo API
            current_app.logger.info("🔑 VEO: Getting authentication token for status check")
            token = self._get_auth_token()
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            current_app.logger.info(f"📋 VEO: Headers prepared for status check: {headers}")
            
            # Use the Veo 3 fetchPredictOperation endpoint
            fetch_url = f"https://{self.location}-aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/{self.location}/publishers/google/models/{self.model_id}:fetchPredictOperation"
            
            request_data = {
                "operationName": operation_name
            }
            
            current_app.logger.info(f"🔍 VEO: Checking video status for: {operation_name}")
            current_app.logger.info(f"🔍 VEO: Fetch URL: {fetch_url}")
            current_app.logger.info(f"🔍 VEO: Request data: {request_data}")
            current_app.logger.info(f"🔍 VEO: About to make POST request to check status")
            
            response = requests.post(fetch_url, headers=headers, json=request_data, timeout=30)
            
            current_app.logger.info(f"📡 VEO: Status check response received")
            current_app.logger.info(f"📡 VEO: Status check response code: {response.status_code}")
            current_app.logger.info(f"📡 VEO: Status check response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                current_app.logger.info(f"✅ VEO: Status check API request successful (200)")
                result = response.json()
                current_app.logger.info(f"📡 VEO: Status check response parsed: {result}")
                current_app.logger.info(f"📡 VEO: Raw response JSON: {result}")
                current_app.logger.info(f"📡 VEO: Response type: {type(result)}")
                current_app.logger.info(f"📡 VEO: Response keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
                
                # Add more detailed logging for debugging
                import json
                current_app.logger.info(f"=== VEO: FULL RESPONSE DEBUG ===")
                current_app.logger.info(f"VEO: Response status code: {response.status_code}")
                current_app.logger.info(f"VEO: Response headers: {dict(response.headers)}")
                current_app.logger.info(f"VEO: Response text length: {len(response.text)}")
                current_app.logger.info(f"VEO: Response text preview: {response.text[:500]}...")
                current_app.logger.info(f"VEO: Parsed result type: {type(result)}")
                if isinstance(result, dict):
                    current_app.logger.info(f"VEO: All result keys: {list(result.keys())}")
                    for key, value in result.items():
                        current_app.logger.info(f"VEO: Key '{key}': {type(value)} = {value}")
                current_app.logger.info(f"=== VEO: END RESPONSE DEBUG ===")
                
                # Check if operation is done
                if result.get('done', False):
                    current_app.logger.info("Operation is done!")
                    current_app.logger.info(f"Full result when done: {result}")
                    
                    # Check for error first
                    if 'error' in result:
                        error = result['error']
                        current_app.logger.error(f"Operation failed with error: {error}")
                        return {
                            'success': False,
                            'status': 'failed',
                            'error': error.get('message', 'Unknown error')
                        }
                    
                    # Operation completed successfully
                    if 'response' in result:
                        current_app.logger.info("Response data found in result")
                        response_data = result['response']
                        current_app.logger.info(f"Response data: {response_data}")
                        current_app.logger.info(f"Response data type: {type(response_data)}")
                        current_app.logger.info(f"Response data keys: {list(response_data.keys()) if isinstance(response_data, dict) else 'Not a dict'}")
                        
                        # Handle Veo 3 response format
                        if 'videos' in response_data:
                            current_app.logger.info("Veo 3 format detected")
                            videos = response_data['videos']
                            current_app.logger.info(f"Videos array: {videos}")
                            if videos and len(videos) > 0:
                                video_data = videos[0]
                                current_app.logger.info(f"First video data: {video_data}")
                                
                                # Check for video data in the response (base64 encoded)
                                if 'bytesBase64Encoded' in video_data:
                                    current_app.logger.info("Found base64 encoded video data")
                                    current_app.logger.info(f"🔍 VEO: Project ID: {self.project_id}")
                                    current_app.logger.info(f"🔍 VEO: Using correct bucket name: prompt-veo-videos")
                                    
                                    # Check if there's a GCS URL in the response
                                    if 'gcsUri' in video_data:
                                        current_app.logger.info(f"🔍 VEO: Found GCS URI in response: {video_data['gcsUri']}")
                                        video_url = video_data['gcsUri']
                                    else:
                                        current_app.logger.warning(f"🔍 VEO: No GCS URI found in response")
                                        current_app.logger.warning(f"🔍 VEO: This should not happen with storageUri specified")
                                        # Don't construct fake URLs - let the error happen
                                        return {
                                            'success': False,
                                            'status': 'failed',
                                            'error': 'No video URL found in Veo response'
                                        }
                                    
                                    current_app.logger.info(f"🔍 VEO: Final video URL: {video_url}")
                                    
                                    return {
                                        'success': True,
                                        'status': 'completed',
                                        'video_url': video_url,
                                        'duration': 60 if 'veo-3.0' in operation_name else 8
                                    }
                                
                                # Check for storage URI
                                video_url = video_data.get('gcsUri') or video_data.get('storageUri')
                                current_app.logger.info(f"Video URL from Veo 3: {video_url}")
                                
                                if video_url:
                                    return {
                                        'success': True,
                                        'status': 'completed',
                                        'video_url': video_url,
                                        'duration': 60 if 'veo-3.0' in operation_name else 8
                                    }
                                else:
                                    current_app.logger.warning("No video URL found in video data")
                                    current_app.logger.info(f"Available video data keys: {list(video_data.keys())}")
                        
                        # Handle legacy response format
                        elif 'predictions' in response_data:
                            current_app.logger.info("Legacy format detected")
                            predictions = response_data['predictions']
                            current_app.logger.info(f"Predictions array: {predictions}")
                            if predictions and len(predictions) > 0:
                                prediction = predictions[0]
                                current_app.logger.info(f"First prediction: {prediction}")
                                
                                # Check for video data in the response (base64 encoded)
                                if 'bytesBase64Encoded' in prediction:
                                    current_app.logger.info("Found base64 encoded video data in prediction")
                                    current_app.logger.info(f"🔍 VEO: Project ID: {self.project_id}")
                                    current_app.logger.info(f"🔍 VEO: Using correct bucket name: prompt-veo-videos")
                                    
                                    # Check if there's a GCS URL in the prediction
                                    if 'gcsUri' in prediction:
                                        current_app.logger.info(f"🔍 VEO: Found GCS URI in prediction: {prediction['gcsUri']}")
                                        video_url = prediction['gcsUri']
                                    else:
                                        current_app.logger.warning(f"🔍 VEO: No GCS URI found in prediction")
                                        current_app.logger.warning(f"🔍 VEO: This should not happen with storageUri specified")
                                        # Don't construct fake URLs - let the error happen
                                        return {
                                            'success': False,
                                            'status': 'failed',
                                            'error': 'No video URL found in Veo response'
                                        }
                                    
                                    current_app.logger.info(f"🔍 VEO: Final video URL: {video_url}")
                                    
                                    return {
                                        'success': True,
                                        'status': 'completed',
                                        'video_url': video_url,
                                        'duration': 60 if 'veo-3.0' in operation_name else 8
                                    }
                                
                                # Check for storage URI
                                video_url = prediction.get('storageUri')
                                current_app.logger.info(f"Video URL from legacy: {video_url}")
                                
                                if video_url:
                                    return {
                                        'success': True,
                                        'status': 'completed',
                                        'video_url': video_url,
                                        'duration': 60 if 'veo-3.0' in operation_name else 8
                                    }
                                else:
                                    current_app.logger.warning("No video URL found in prediction")
                                    current_app.logger.info(f"Available prediction keys: {list(prediction.keys())}")
                        
                        # Check for other possible video URL fields
                        else:
                            current_app.logger.warning("No videos or predictions found, checking for other fields")
                            current_app.logger.info(f"All response_data keys: {list(response_data.keys())}")
                            
                            # Look for any field that might contain a video URL
                            for key, value in response_data.items():
                                current_app.logger.info(f"Checking field '{key}': {value}")
                                if isinstance(value, str) and ('gs://' in value or 'http' in value):
                                    current_app.logger.info(f"Found potential video URL in field '{key}': {value}")
                                    return {
                                        'success': True,
                                        'status': 'completed',
                                        'video_url': value,
                                        'duration': 60 if 'veo-3.0' in operation_name else 8
                                    }
                    
                    else:
                        current_app.logger.warning("No response data found in result")
                        current_app.logger.info(f"Available keys in result: {list(result.keys())}")
                        
                        # Check if video URL might be directly in the result
                        for key, value in result.items():
                            current_app.logger.info(f"Checking result field '{key}': {value}")
                            if isinstance(value, str) and ('gs://' in value or 'http' in value):
                                current_app.logger.info(f"Found potential video URL in result field '{key}': {value}")
                                return {
                                    'success': True,
                                    'status': 'completed',
                                    'video_url': value,
                                    'duration': 60 if 'veo-3.0' in operation_name else 8
                                }
                    
                    # If we get here, operation is done but no video data found
                    current_app.logger.warning("Operation done but no video data found")
                    current_app.logger.info(f"Full result structure: {result}")
                    
                    # Try to extract any GCS URL from the entire response
                    import json
                    response_str = json.dumps(result, indent=2)
                    current_app.logger.info(f"Full response as string: {response_str}")
                    
                    # Look for any GCS URL pattern in the entire response
                    import re
                    gcs_pattern = r'gs://[^\s"\']+\.mp4'
                    gcs_matches = re.findall(gcs_pattern, response_str)
                    current_app.logger.info(f"GCS URL matches found: {gcs_matches}")
                    
                    if gcs_matches:
                        video_url = gcs_matches[0]
                        current_app.logger.info(f"Found GCS URL in response: {video_url}")
                        return {
                            'success': True,
                            'status': 'completed',
                            'video_url': video_url,
                            'duration': 60 if 'veo-3.0' in operation_name else 8
                        }
                    
                    # NEW: Try to construct the expected GCS URL based on operation name
                    current_app.logger.info("Attempting to construct expected GCS URL from operation name")
                    operation_id = operation_name.split('/')[-1]
                    bucket_name = "prompt-veo-videos"
                    expected_gcs_url = f"gs://{bucket_name}/videos/{operation_id}.mp4"
                    current_app.logger.info(f"Expected GCS URL: {expected_gcs_url}")
                    
                    # Check if the file exists in GCS
                    try:
                        from google.cloud import storage
                        storage_client = storage.Client()
                        bucket = storage_client.bucket(bucket_name)
                        blob = bucket.blob(f"videos/{operation_id}.mp4")
                        
                        if blob.exists():
                            current_app.logger.info(f"✅ Found video file in GCS: {expected_gcs_url}")
                            return {
                                'success': True,
                                'status': 'completed',
                                'video_url': expected_gcs_url,
                                'duration': 60 if 'veo-3.0' in operation_name else 8
                            }
                        else:
                            current_app.logger.warning(f"❌ Expected video file not found in GCS: {expected_gcs_url}")
                    except Exception as gcs_error:
                        current_app.logger.error(f"❌ Error checking GCS for expected file: {gcs_error}")
                    
                    # No video data found - this is an error
                    current_app.logger.error("❌ No video data found in completed operation")
                    current_app.logger.error(f"❌ Full response structure: {result}")
                    return {
                        'success': False,
                        'status': 'failed',
                        'error': 'No video data found in completed operation'
                    }
                
                elif result.get('error'):
                    # Operation failed
                    error = result['error']
                    current_app.logger.error(f"Operation failed with error: {error}")
                    return {
                        'success': False,
                        'status': 'failed',
                        'error': error.get('message', 'Unknown error')
                    }
                
                else:
                    # Operation still processing
                    current_app.logger.info("Operation still processing...")
                    return {
                        'success': True,
                        'status': 'processing'
                    }
                
            else:
                error_msg = f"Status check failed: {response.status_code} - {response.text}"
                current_app.logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }
                
        except Exception as e:
            current_app.logger.error(f"Error checking video status: {e}")
            return {
                'success': False,
                'error': str(e)
            } 
