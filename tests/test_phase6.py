import pytest
import json
from unittest.mock import MagicMock, patch
from app import create_app, db
from app.models import User, Video, ApiUsage

@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def user(app):
    user = User(
        email='test@example.com',
        username='testuser',
        credits=10,
        subscription_tier='basic'
    )
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def auth_headers(user):
    return {'Authorization': 'Bearer test-token'}

@pytest.fixture
def mock_auth(monkeypatch):
    """Mock authentication for testing"""
    def mock_login_required(f):
        def decorated_function(*args, **kwargs):
            from flask import request
            request.user_id = 1
            request.current_user = MagicMock(id=1)
            return f(*args, **kwargs)
        return decorated_function
    
    def mock_verify_token(token):
        return 1  # Return user ID 1
    
    monkeypatch.setattr('app.auth.utils.login_required', mock_login_required)
    monkeypatch.setattr('app.auth.utils.verify_token', mock_verify_token)

class TestPhase6Features:
    def test_user_rate_limiting(self, app, user):
        """Test user rate limiting functionality"""
        # Test initial state
        assert user.api_calls_today == 0
        assert user.can_make_api_call() is True
        
        # Test recording API calls
        user.record_api_call()
        assert user.api_calls_today == 1
        assert user.can_make_api_call() is True
        
        # Test rate limit info
        rate_info = user.get_rate_limit_info()
        assert rate_info['tier'] == 'development'  # In testing mode, tier is 'development'
        assert rate_info['limit'] == 1000  # Development limit is 1000
        assert rate_info['used'] == 1
        assert rate_info['remaining'] == 999
    
    def test_video_priority_calculation(self, app, user):
        """Test video priority calculation"""
        # Create a video
        video = Video(
            user_id=user.id,
            prompt='Test video',
            quality='1080p'
        )
        db.session.add(video)
        db.session.commit()
        
        # Test priority calculation
        priority = video.calculate_priority()
        assert priority > 0  # Should have some priority
        
        # Test priority update
        video.update_priority()
        assert video.priority > 0
    
    def test_queue_position_calculation(self, app, user):
        """Test queue position calculation"""
        # Create multiple videos
        video1 = Video(
            user_id=user.id,
            prompt='Video 1',
            quality='360p',
            status='pending'
        )
        video2 = Video(
            user_id=user.id,
            prompt='Video 2',
            quality='1080p',
            status='pending'
        )
        db.session.add_all([video1, video2])
        db.session.commit()
        
        # Test queue position
        from app.main.routes import get_queue_position
        position1 = get_queue_position(video1.id)
        position2 = get_queue_position(video2.id)
        
        assert position1 is not None
        assert position2 is not None
        assert position1 != position2
    
    def test_api_usage_tracking(self, app, user):
        """Test API usage tracking"""
        # Create API usage record
        usage = ApiUsage(
            user_id=user.id,
            endpoint='generate_video',
            method='POST',
            response_time=1.5,
            status_code=200,
            user_agent='test-agent',
            ip_address='127.0.0.1'
        )
        db.session.add(usage)
        db.session.commit()
        
        # Verify it was created
        assert usage.id is not None
        assert usage.user_id == user.id
        assert usage.endpoint == 'generate_video'
        assert usage.response_time == 1.5
    
    def test_subscription_tier_upgrade(self, app, user):
        """Test subscription tier upgrade"""
        # Test upgrading to pro tier
        from app.auth.rate_limit import update_user_subscription_tier
        
        success = update_user_subscription_tier(user.id, 'pro')
        assert success is True
        
        # Verify tier was updated
        user = User.query.get(user.id)
        assert user.subscription_tier == 'pro'
        
        # Test rate limits for pro tier
        rate_info = user.get_rate_limit_info()
        assert rate_info['limit'] == 1000
    
    def test_queue_status_endpoint(self, client, user, auth_headers, mock_auth):
        """Test queue status endpoint"""
        # Create a pending video
        video = Video(
            user_id=user.id,
            prompt='Test video',
            quality='360p',
            status='pending'
        )
        db.session.add(video)
        db.session.commit()
        
        response = client.get('/api/queue/status', headers=auth_headers)
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'user_videos' in data
        assert 'queue_stats' in data
        assert 'rate_limit_info' in data
    
    def test_rate_limit_status_endpoint(self, client, user, auth_headers, mock_auth):
        """Test rate limit status endpoint"""
        response = client.get('/api/rate-limits/status', headers=auth_headers)
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'rate_limit_info' in data
        assert 'subscription_tier' in data
        assert data['subscription_tier'] == 'basic' 