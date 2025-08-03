"""
Mock Veo API implementation for testing and development
"""
import time
import uuid
from datetime import datetime, timedelta

class MockVeoAPI:
    def __init__(self):
        self.jobs = {}
    
    def generate_video(self, prompt, quality, duration=5):
        """Mock video generation"""
        job_id = str(uuid.uuid4())
        
        # Simulate different processing times based on quality
        processing_time = 10 if quality == 'free' else 30  # seconds
        
        self.jobs[job_id] = {
            'id': job_id,
            'prompt': prompt,
            'quality': quality,
            'duration': duration,
            'status': 'processing',
            'created_at': datetime.utcnow(),
            'estimated_completion': datetime.utcnow() + timedelta(seconds=processing_time),
            'video_url': f"https://mock-veo.com/videos/{job_id}.mp4"
        }
        
        return {
            'success': True,
            'job_id': job_id,
            'estimated_time': processing_time
        }
    
    def check_status(self, job_id):
        """Check job status"""
        if job_id not in self.jobs:
            return {'status': 'failed', 'error': 'Job not found'}
        
        job = self.jobs[job_id]
        
        # Check if job is complete
        if datetime.utcnow() >= job['estimated_completion']:
            job['status'] = 'completed'
            return {
                'status': 'completed',
                'video_url': job['video_url'],
                'duration': job['duration']
            }
        
        return {
            'status': 'processing',
            'progress': min(90, int((datetime.utcnow() - job['created_at']).total_seconds() / 
                                   (job['estimated_completion'] - job['created_at']).total_seconds() * 100))
        }
    
    def download_video(self, job_id):
        """Mock video download"""
        if job_id not in self.jobs:
            return None
        
        job = self.jobs[job_id]
        if job['status'] != 'completed':
            return None
        
        # Return mock video content
        return b'mock_video_content'

# Global instance
mock_veo = MockVeoAPI() 