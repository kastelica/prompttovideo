#!/usr/bin/env python3
"""
Basic tests for the application
"""

import pytest
from app import create_app, db
from app.models import User, Video


@pytest.fixture
def app():
    """Create application for testing"""
    app = create_app('testing')
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create test runner"""
    return app.test_cli_runner()


class TestBasicFunctionality:
    """Test basic application functionality"""
    
    def test_app_creation(self, app):
        """Test that app can be created"""
        assert app is not None
        assert app.config['TESTING'] is True
    
    def test_home_page(self, client):
        """Test that home page loads"""
        response = client.get('/')
        assert response.status_code == 200
    
    def test_database_connection(self, app):
        """Test database connection"""
        with app.app_context():
            # Test that we can query the database
            users = User.query.all()
            assert isinstance(users, list)
    
    def test_video_model(self, app):
        """Test Video model"""
        with app.app_context():
            videos = Video.query.all()
            assert isinstance(videos, list)


class TestGCSUtils:
    """Test GCS utilities"""
    
    def test_get_gcs_bucket_name(self, app):
        """Test getting GCS bucket name"""
        with app.app_context():
            from app.gcs_utils import get_gcs_bucket_name
            bucket_name = get_gcs_bucket_name()
            # In test environment, it should use the config value
            assert bucket_name in ['test-bucket', 'prompt-veo-videos']
    
    def test_sanitize_filename(self, app):
        """Test filename sanitization"""
        with app.app_context():
            from app.gcs_utils import sanitize_filename
            # Test basic sanitization
            result = sanitize_filename("test file.mp4")
            assert result == "test_file.mp4"
            
            # Test special characters
            result = sanitize_filename("test@#$%^&*()file.mp4")
            assert result == "test_________file.mp4"
    
    def test_generate_video_filename(self, app):
        """Test video filename generation"""
        with app.app_context():
            from app.gcs_utils import generate_video_filename
            gcs_path, filename, gcs_url = generate_video_filename(
                video_id=123,
                quality='free',
                prompt='test prompt'
            )
            assert 'videos/' in gcs_path
            assert '123_' in filename
            assert filename.endswith('.mp4')
            assert gcs_url.startswith('gs://')


class TestModels:
    """Test database models"""
    
    def test_user_model(self, app):
        """Test User model"""
        with app.app_context():
            user = User(
                email='test@example.com',
                username='testuser',
                password_hash='hashed_password'
            )
            assert user.email == 'test@example.com'
            assert user.username == 'testuser'
    
    def test_video_model(self, app):
        """Test Video model"""
        with app.app_context():
            video = Video(
                title='Test Video',
                prompt='Test prompt',
                quality='free',
                status='pending'
            )
            assert video.title == 'Test Video'
            assert video.prompt == 'Test prompt'
            assert video.quality == 'free'
            assert video.status == 'pending'


if __name__ == '__main__':
    pytest.main([__file__]) 