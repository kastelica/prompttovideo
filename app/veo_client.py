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
        
        # Check if we should use mock mode first
        if self._should_use_mock():
            current_app.logger.info("VeoClient initialized in mock mode - skipping Google Cloud authentication")
            return
        
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
            try:
                self.credentials = service_account.Credentials.from_service_account_file(
                    creds_path,
                    scopes=['https://www.googleapis.com/auth/cloud-platform']
                )
                current_app.logger.info(f"Loaded Google Cloud credentials from: {creds_path}")
            except Exception as e:
                current_app.logger.error(f"Failed to load credentials from {creds_path}: {e}")
        else:
            current_app.logger.warning(f"Credentials file not found: {creds_path}")
    
    def _init_google_auth(self):
        """Initialize Google Cloud authentication"""
        try:
            # Try to use service account credentials from environment variable
            credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            logger.info(f"DEBUG: GOOGLE_APPLICATION_CREDENTIALS path: {credentials_path}")
            
            if credentials_path:
                logger.info(f"DEBUG: Credentials path exists: {os.path.exists(credentials_path)}")
                if os.path.exists(credentials_path):
                    logger.info("DEBUG: Loading service account credentials from file")
                    from google.oauth2 import service_account
                    self.credentials = service_account.Credentials.from_service_account_file(
                        credentials_path,
                        scopes=['https://www.googleapis.com/auth/cloud-platform']
                    )
                    logger.info("DEBUG: Service account credentials loaded successfully")
                    logger.info(f"DEBUG: Credentials valid: {self.credentials.valid}")
                    logger.info("Google Cloud authentication initialized with service account")
                else:
                    logger.warning(f"DEBUG: Credentials file does not exist: {credentials_path}")
                    self.credentials = None
            else:
                logger.warning("DEBUG: GOOGLE_APPLICATION_CREDENTIALS environment variable not set")
                # Fallback to Application Default Credentials
                logger.info("DEBUG: Trying Application Default Credentials")
                import google.auth
                from google.auth.transport.requests import Request
                
                credentials, project = google.auth.default()
                if not credentials.valid:
                    credentials.refresh(Request())
                
                self.credentials = credentials
                logger.info("DEBUG: Application Default Credentials loaded")
                logger.info(f"DEBUG: Credentials valid: {self.credentials.valid}")
                logger.info("Google Cloud authentication initialized with default credentials")
            
        except Exception as e:
            logger.error(f"DEBUG: Google Cloud authentication failed with exception: {e}")
            logger.warning(f"Google Cloud authentication failed: {e}")
            logger.info("You may need to set up Google Cloud credentials")
            self.credentials = None
    
    def _get_auth_token(self):
        """Get authentication token for Google Cloud API"""
        try:
            # Check if we should use mock mode first
            if self._should_use_mock():
                current_app.logger.info("Using mock authentication token for development")
                return "mock_token_for_development"
            
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
    
    def _should_use_mock(self):
        """Check if we should use mock mode for development"""
        # Check for explicit mock mode
        if current_app.config.get('VEO_MOCK_MODE', False):
            current_app.logger.info("🎭 VEO: Mock mode enabled via VEO_MOCK_MODE=True")
            return True
            
        # Check for testing mode
        if current_app.config.get('TESTING', False):
            current_app.logger.info("🎭 VEO: Mock mode enabled via TESTING=True")
            return True
            
        # Check for development mode
        if current_app.config.get('FLASK_ENV') == 'development':
            current_app.logger.info("🎭 VEO: Mock mode enabled via FLASK_ENV=development")
            return True
            
        # Check for cost prevention mode
        if current_app.config.get('VEO_PREVENT_CHARGES', False):
            current_app.logger.warning("💰 VEO: Real API calls disabled via VEO_PREVENT_CHARGES=True")
            current_app.logger.warning("💰 VEO: Using mock mode to prevent charges")
            return True
            
        return False
    
    def generate_video(self, prompt, quality='free', duration=30):
        """Generate video using Veo API"""
        current_app.logger.info(f"🌐 VEO: ===== VEO API: GENERATE VIDEO STARTED =====")
        current_app.logger.info(f"🌐 VEO: Prompt: '{prompt}'")
        current_app.logger.info(f"🌐 VEO: Quality: {quality}")
        current_app.logger.info(f"🌐 VEO: Duration: {duration}")
        current_app.logger.info(f"🌐 VEO: Prompt type: {type(prompt)}")
        current_app.logger.info(f"🌐 VEO: Quality type: {type(quality)}")
        current_app.logger.info(f"🌐 VEO: Duration type: {type(duration)}")
        
        # Set model based on quality
        if quality == 'free':
            self.model_id = 'veo-2.0-generate-001'  # Veo 2 for free tier
            max_duration = 8  # Veo 2 supports up to 8 seconds
            has_audio = False
        else:  # premium
            self.model_id = 'veo-3.0-generate-001'  # Veo 3 for premium tier
            max_duration = 60  # Veo 3 supports up to 60 seconds
            has_audio = True
        
        current_app.logger.info(f"🎯 VEO: Using model: {self.model_id}")
        current_app.logger.info(f"🎯 VEO: Max duration: {max_duration} seconds")
        current_app.logger.info(f"🎯 VEO: Has audio: {has_audio}")
        
        try:
            # Check if we should use mock mode
            if self._should_use_mock():
                current_app.logger.info("🎭 VEO: Using mock Veo API for development")
                result = self._mock_generate_video(prompt, quality, duration)
                current_app.logger.info(f"🎭 VEO: Mock result: {result}")
                current_app.logger.info(f"🌐 VEO: ===== VEO API: GENERATE VIDEO COMPLETED (MOCK) =====")
                return result
            
            # ⚠️ COST WARNING: Real Veo API calls will charge you money
            current_app.logger.warning("💰 VEO: WARNING - Real Veo API calls will charge your Google Cloud account")
            current_app.logger.warning("💰 VEO: Each video generation costs money, even if it fails")
            current_app.logger.warning("💰 VEO: Consider using VEO_MOCK_MODE=True for testing")
            
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
                    "storageUri": "gs://prompt-veo-videos/videos/"
                }
            }
            
            # Add audio generation for premium (Veo 3)
            if has_audio:
                request_data["parameters"]["generateAudio"] = True
            
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
    
    def _mock_generate_video(self, prompt, quality, duration):
        """Mock video generation for development/testing"""
        import uuid
        import time
        
        # Generate a mock operation name
        operation_name = f"projects/{self.project_id}/locations/{self.location}/publishers/google/models/{self.model_id}/operations/{uuid.uuid4()}"
        
        current_app.logger.info(f"Mock video generation started: {operation_name}")
        
        return {
            'success': True,
            'operation_name': operation_name
        }
    
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
            # Check if we should use mock mode
            if self._should_use_mock():
                current_app.logger.info("🎭 VEO: Using mock status check for development")
                result = self._mock_check_video_status(operation_name)
                current_app.logger.info(f"🎭 VEO: Mock status result: {result}")
                current_app.logger.info(f"🔍 VEO: ===== VEO API: CHECK STATUS COMPLETED (MOCK) =====")
                return result
            
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
    
    def _mock_check_video_status(self, operation_name):
        """Mock video status check for development"""
        current_app.logger.info(f"🎭 Mock status check for operation: {operation_name}")
        
        # Determine duration based on model
        duration = 60 if 'veo-3.0' in operation_name else 8
        
        # Simulate a completed video with proper duration
        # Return a GCS URL that will be downloaded to local
        mock_video_url = f"gs://mock-bucket/videos/mock-{operation_name.split('-')[-1]}.mp4"
        
        return {
            'success': True,
            'status': 'completed',
            'video_url': mock_video_url,
            'duration': duration
        } 
