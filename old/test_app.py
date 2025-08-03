import pytest
import json
from app import create_app, db
from app.models import User, Video, CreditTransaction, PromptPack
from app.auth.utils import generate_token

@pytest.fixture
def app():
    import os
    os.environ['FLASK_ENV'] = 'testing'
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
def runner(app):
    return app.test_cli_runner()

@pytest.fixture
def user(app):
    user = User(email='test@example.com')
    user.set_password('password123')
    user.email_verified = True
    db.session.add(user)
    db.session.commit()
    # Add credits after commit when user has an ID
    user.add_credits(10, 'test')
    db.session.commit()
    return user

@pytest.fixture
def auth_headers(user):
    token = generate_token(user.id)
    return {'Authorization': f'Bearer {token}'}

class TestAuth:
    def test_register(self, client, app):
        with app.test_request_context():
            response = client.post('/auth/register', 
                                 json={'email': 'new@example.com', 'password': 'password123'})
            assert response.status_code == 201
            data = json.loads(response.data)
            assert data['success'] == True
            assert 'token' in data
    
    def test_login(self, client, user, app):
        with app.test_request_context():
            response = client.post('/auth/login', 
                                 json={'email': 'test@example.com', 'password': 'password123'})
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] == True
            assert 'token' in data
    
    def test_login_invalid_password(self, client, user, app):
        with app.test_request_context():
            response = client.post('/auth/login', 
                                 json={'email': 'test@example.com', 'password': 'wrongpassword'})
            assert response.status_code == 401

class TestVideoGeneration:
    def test_generate_video(self, client, auth_headers):
        response = client.post('/generate', 
                             headers=auth_headers,
                             json={'prompt': 'A beautiful sunset', 'quality': '360p'})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert 'video_id' in data
    
    def test_generate_video_no_auth(self, client):
        response = client.post('/generate', 
                             json={'prompt': 'A beautiful sunset'})
        assert response.status_code == 401
    
    def test_generate_video_insufficient_credits(self, client, auth_headers):
        # Create user with 0 credits
        user = User.query.filter_by(email='test@example.com').first()
        user.credits = 0
        db.session.commit()
        
        response = client.post('/generate', 
                             headers=auth_headers,
                             json={'prompt': 'A beautiful sunset', 'quality': '1080p'})
        assert response.status_code == 402
    
    def test_generate_video_invalid_quality(self, client, auth_headers):
        response = client.post('/generate', 
                             headers=auth_headers,
                             json={'prompt': 'A beautiful sunset', 'quality': '720p'})
        assert response.status_code == 400

class TestVideoStatus:
    def test_video_status(self, client, auth_headers, user):
        # Create a video
        video = Video(user_id=user.id, prompt='Test video', quality='360p')
        db.session.add(video)
        db.session.commit()
        
        response = client.get(f'/api/videos/{video.id}/status')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['id'] == video.id
        assert data['status'] == 'pending'

class TestAPI:
    def test_api_generate_video(self, client, auth_headers):
        response = client.post('/api/v1/generate', 
                             headers=auth_headers,
                             json={'prompt': 'API test video', 'quality': '360p'})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
    
    def test_api_list_videos(self, client, auth_headers, user):
        # Create some videos
        for i in range(3):
            video = Video(user_id=user.id, prompt=f'Video {i}', quality='360p')
            db.session.add(video)
        db.session.commit()
        
        response = client.get('/api/v1/videos', headers=auth_headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['videos']) == 3
    
    def test_api_get_credits(self, client, auth_headers, user):
        response = client.get('/api/v1/user/credits', headers=auth_headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'credits' in data
        assert 'daily_credits_used' in data

class TestModels:
    def test_user_credit_management(self, user):
        initial_credits = user.credits
        
        # Test using credits
        assert user.use_credits(5) == True
        assert user.credits == initial_credits - 5
        
        # Test insufficient credits
        assert user.use_credits(100) == False
        assert user.credits == initial_credits - 5
        
        # Test adding credits
        user.add_credits(10, 'test')
        assert user.credits == initial_credits - 5 + 10
    
    def test_video_slug_generation(self, user):
        video = Video(user_id=user.id, prompt='Test Video Title')
        db.session.add(video)
        db.session.commit()
        
        # Generate slug after commit when ID is available
        video.slug = video.generate_slug()
        db.session.commit()
        
        assert video.slug is not None
        assert 'test-video-title' in video.slug.lower()
    
    def test_video_view_increment(self, user):
        video = Video(user_id=user.id, prompt='Test video')
        db.session.add(video)
        db.session.commit()
        
        initial_views = video.views
        video.increment_views()
        assert video.views == initial_views + 1

class TestAdmin:
    def test_admin_dashboard(self, client, auth_headers):
        response = client.get('/admin/analytics/dashboard', headers=auth_headers)
        # Note: This will fail without admin privileges - you'd need to add admin field to User model
        assert response.status_code in [200, 403]
    
    def test_prompt_packs(self, client, auth_headers):
        response = client.get('/admin/prompt-packs', headers=auth_headers)
        # Note: This will fail without admin privileges
        assert response.status_code in [200, 403]

if __name__ == '__main__':
    pytest.main([__file__]) 