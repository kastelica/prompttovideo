#!/usr/bin/env python3
"""
Pytest configuration and fixtures
"""

import pytest
import os
import tempfile
from app import create_app, db
from app.models import User, Video


@pytest.fixture(scope='session')
def app():
    """Create application for testing"""
    # Create a temporary database file
    db_fd, db_path = tempfile.mkstemp()
    
    app = create_app('testing')
    app.config.update({
        'TESTING': True,
        'DATABASE_URL': f'sqlite:///{db_path}',
        'GCS_BUCKET_NAME': 'test-bucket',
    
        'SECRET_KEY': 'test-secret-key',
        'JWT_SECRET_KEY': 'test-jwt-secret'
    })
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()
    
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create test runner"""
    return app.test_cli_runner()


@pytest.fixture
def sample_user(app):
    """Create a sample user for testing"""
    with app.app_context():
        user = User(
            email='test@example.com',
            username='testuser',
            password_hash='hashed_password'
        )
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def sample_video(app, sample_user):
    """Create a sample video for testing"""
    with app.app_context():
        video = Video(
            title='Test Video',
            prompt='Test prompt',
            quality='free',
            status='completed',
            user_id=sample_user.id,
            public=True
        )
        db.session.add(video)
        db.session.commit()
        return video 