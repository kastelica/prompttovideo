import pytest
from app import create_app, db
from app.models import User, Video, Referral, PromptPack
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

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
    user = User(email='test@example.com')
    user.set_password('password')
    user.email_verified = True
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def auth_headers(user):
    with patch('app.auth.utils.verify_token') as mock_verify:
        mock_verify.return_value = user.id
        return {'Authorization': 'Bearer test-token'}

@pytest.fixture
def mock_auth():
    with patch('app.auth.utils.login_required') as mock_login_required:
        mock_login_required.return_value = lambda f: f
        with patch('app.auth.utils.verify_token') as mock_verify:
            mock_verify.return_value = 1
            yield mock_verify

class TestPhase7Features:
    """Test Phase 7 features: Referral system, Developer API, Deployment configs"""
    
    def test_referral_model_creation(self, app, user):
        """Test referral model and relationships"""
        # Create a referrer and referred user
        referrer = User(email='referrer@example.com')
        referred = User(email='referred@example.com')
        db.session.add_all([referrer, referred])
        db.session.commit()
        
        # Create referral
        referral = Referral(
            referrer_id=referrer.id,
            referred_id=referred.id,
            referrer_code=referrer.referral_code
        )
        db.session.add(referral)
        db.session.commit()
        
        assert referral.referrer_id == referrer.id
        assert referral.referred_id == referred.id
        assert referral.referrer_code == referrer.referral_code
        assert referral.created_at is not None
        
        # Test relationships
        assert len(referrer.referrals_given) == 1
        assert len(referred.referrals_received) == 1
        assert referrer.referrals_given[0].referred_id == referred.id
    
    def test_user_referral_stats(self, app, user):
        """Test user referral statistics"""
        # Create referred users
        referred1 = User(email='referred1@example.com', referred_by=user.referral_code)
        referred2 = User(email='referred2@example.com', referred_by=user.referral_code)
        db.session.add_all([referred1, referred2])
        db.session.commit()
        
        # Process referrals
        user.process_referral_signup(referred1)
        user.process_referral_signup(referred2)
        db.session.commit()
        
        # Get stats
        stats = user.get_referral_stats()
        
        assert stats['referral_code'] == user.referral_code
        assert stats['referred_users'] == 2
        assert stats['total_earned'] == 10  # 5 credits per referral
        assert 'referral_url' in stats
    
    def test_referral_landing_page(self, client, user):
        """Test referral landing page"""
        response = client.get(f'/ref/{user.referral_code}')
        assert response.status_code == 200
        assert user.referral_code.encode() in response.data
    
    def test_invalid_referral_code(self, client):
        """Test invalid referral code handling"""
        response = client.get('/ref/INVALID')
        assert response.status_code == 302  # Redirect to index
    
    def test_developer_api_generate_video(self, client, user, auth_headers):
        """Test developer API video generation"""
        with patch('app.tasks.generate_video_task.delay'):
            response = client.post('/api/v1/generate', 
                headers=auth_headers,
                json={
                    'prompt': 'Test video generation',
                    'quality': '360p'
                }
            )
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert 'video_id' in data
            assert data['status'] == 'pending'
            assert 'credits_remaining' in data
            assert 'queue_position' in data
            assert 'estimated_wait_time' in data
    
    def test_developer_api_video_status(self, client, user, auth_headers):
        """Test developer API video status endpoint"""
        # Create a video
        video = Video(
            user_id=user.id,
            prompt='Test video',
            quality='360p',
            status='completed',
            gcs_signed_url='https://example.com/video.mp4',
            duration=30,
            thumbnail_url='https://example.com/thumb.jpg'
        )
        db.session.add(video)
        db.session.commit()
        
        response = client.get(f'/api/v1/video/{video.id}/status', headers=auth_headers)
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['video_id'] == video.id
        assert data['status'] == 'completed'
        assert data['video_url'] == video.gcs_signed_url
        assert data['duration'] == 30
        assert data['thumbnail_url'] == video.thumbnail_url
    
    def test_developer_api_list_videos(self, client, user, auth_headers):
        """Test developer API list videos endpoint"""
        # Create videos
        video1 = Video(user_id=user.id, prompt='Video 1', quality='360p', status='completed')
        video2 = Video(user_id=user.id, prompt='Video 2', quality='1080p', status='pending')
        db.session.add_all([video1, video2])
        db.session.commit()
        
        response = client.get('/api/v1/videos', headers=auth_headers)
        assert response.status_code == 200
        
        data = response.get_json()
        assert len(data['videos']) == 2
        assert data['pagination']['total'] == 2
        assert data['pagination']['page'] == 1
    
    def test_developer_api_account_info(self, client, user, auth_headers):
        """Test developer API account information endpoint"""
        response = client.get('/api/v1/account', headers=auth_headers)
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['user_id'] == user.id
        assert data['email'] == user.email
        assert data['credits'] == user.credits
        assert data['subscription_tier'] == user.subscription_tier
        assert 'rate_limit_info' in data
    
    def test_developer_api_queue_status(self, client, user, auth_headers):
        """Test developer API queue status endpoint"""
        # Create pending video
        video = Video(
            user_id=user.id,
            prompt='Test video',
            quality='360p',
            status='pending'
        )
        db.session.add(video)
        db.session.commit()
        
        response = client.get('/api/v1/queue/status', headers=auth_headers)
        assert response.status_code == 200
        
        data = response.get_json()
        assert len(data['user_videos']) == 1
        assert data['queue_stats']['user_pending_count'] == 1
        assert data['queue_stats']['total_pending'] >= 1
    
    def test_api_documentation_page(self, client):
        """Test API documentation page"""
        response = client.get('/api/docs')
        assert response.status_code == 200
        assert b'API Documentation' in response.data
        assert b'Getting Started' in response.data
        assert b'Rate Limits' in response.data
    
    def test_referral_dashboard_page(self, client, user):
        """Test referral dashboard page"""
        with patch('app.auth.utils.login_required') as mock_login:
            mock_login.return_value = lambda f: f
            with patch('app.auth.utils.verify_token') as mock_verify:
                mock_verify.return_value = user.id
                
                response = client.get('/referral/dashboard')
                assert response.status_code == 200
                assert b'Referral Dashboard' in response.data
                assert user.referral_code.encode() in response.data
    
    def test_referral_stats_api(self, client, user):
        """Test referral stats API endpoint"""
        with patch('app.auth.utils.login_required') as mock_login:
            mock_login.return_value = lambda f: f
            with patch('app.auth.utils.verify_token') as mock_verify:
                mock_verify.return_value = user.id
                
                response = client.get('/api/referral/stats')
                assert response.status_code == 200
                
                data = response.get_json()
                assert 'stats' in data
                assert 'recent_referrals' in data
                assert data['stats']['referral_code'] == user.referral_code
    
    def test_referral_code_validation(self, client, user):
        """Test referral code validation API"""
        response = client.get(f'/api/referral/validate?code={user.referral_code}')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['valid'] is True
        assert data['referrer_email'] == user.email
        
        # Test invalid code
        response = client.get('/api/referral/validate?code=INVALID')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['valid'] is False
        assert 'error' in data
    
    def test_referral_share_api(self, client, user):
        """Test referral share content API"""
        with patch('app.auth.utils.login_required') as mock_login:
            mock_login.return_value = lambda f: f
            with patch('app.auth.utils.verify_token') as mock_verify:
                mock_verify.return_value = user.id
                
                response = client.get('/api/referral/share')
                assert response.status_code == 200
                
                data = response.get_json()
                assert 'twitter' in data
                assert 'facebook' in data
                assert 'linkedin' in data
                assert 'email' in data
                assert 'url' in data
                assert user.referral_code in data['twitter']
    
    def test_deployment_configs_exist(self):
        """Test that deployment configuration files exist"""
        import os
        
        # Check for Railway config
        assert os.path.exists('railway.json')
        
        # Check for Cloud Build config
        assert os.path.exists('cloudbuild.yaml')
        
        # Check for deployment script
        assert os.path.exists('deploy.sh')
        
        # Check for Dockerfile
        assert os.path.exists('Dockerfile')
    
    def test_railway_config_structure(self):
        """Test Railway configuration structure"""
        import json
        
        with open('railway.json', 'r') as f:
            config = json.load(f)
        
        assert 'build' in config
        assert 'deploy' in config
        assert config['build']['builder'] == 'DOCKERFILE'
        assert config['deploy']['startCommand'] is not None
    
    def test_cloudbuild_config_structure(self):
        """Test Cloud Build configuration structure"""
        with open('cloudbuild.yaml', 'r') as f:
            content = f.read()
        
        assert 'steps:' in content
        assert 'gcr.io/cloud-builders/docker' in content
        assert 'gcloud' in content
        assert 'run deploy' in content
    
    def test_deploy_script_structure(self):
        """Test deployment script structure"""
        with open('deploy.sh', 'r') as f:
            content = f.read()
        
        assert '#!/bin/bash' in content
        assert 'DEPLOY_TARGET' in content
        assert 'cloudrun' in content
        assert 'railway' in content
        assert 'gcloud builds submit' in content
    
    def test_referral_self_referral_prevention(self, app, user):
        """Test that users cannot refer themselves"""
        # Try to process self-referral
        result = user.process_referral_signup(user)
        assert result is False
        
        # Check that no credits were added
        original_credits = user.credits
        user.process_referral_signup(user)
        assert user.credits == original_credits
    
    def test_referral_credit_distribution(self, app, user):
        """Test referral credit distribution"""
        # Create referred user
        referred = User(email='referred@example.com')
        db.session.add(referred)
        db.session.commit()
        
        # Get initial credits
        initial_referrer_credits = user.credits
        initial_referred_credits = referred.credits
        
        # Process referral
        user.process_referral_signup(referred)
        db.session.commit()
        
        # Check credit distribution
        assert user.credits == initial_referrer_credits + 5
        assert referred.credits == initial_referred_credits + 5
        
        # Check referral record
        referral = Referral.query.filter_by(
            referrer_id=user.id,
            referred_id=referred.id
        ).first()
        assert referral is not None
        assert referral.referrer_code == user.referral_code 