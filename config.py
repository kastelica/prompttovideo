import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://localhost/prompttovideo'
    
    # Redis configuration
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    
    # Celery configuration
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL') or REDIS_URL
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND') or REDIS_URL
    
    # Mail configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    
    # Stripe configuration
    STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
    STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')
    
    # Google Cloud Storage
    GCS_BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME') or 'prompttovideo-videos'
    GOOGLE_APPLICATION_CREDENTIALS = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    
    # Veo API configuration
    VEO_API_KEY = os.environ.get('VEO_API_KEY')
    VEO_API_URL = os.environ.get('VEO_API_URL') or 'https://api.veo.ai'
    VEO_MOCK_MODE = os.environ.get('VEO_MOCK_MODE', 'false').lower() in ['true', 'on', '1']
    
    # Sentry configuration
    SENTRY_DSN = os.environ.get('SENTRY_DSN')
    
    # Rate limiting
    RATELIMIT_STORAGE_URL = REDIS_URL
    RATELIMIT_DEFAULT = "100 per hour"
    
    # JWT configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    
    # Credit system
    DAILY_FREE_CREDITS = int(os.environ.get('DAILY_FREE_CREDITS') or 3)
    CREDIT_COST_FREE = int(os.environ.get('CREDIT_COST_FREE') or 1)
    CREDIT_COST_PREMIUM = int(os.environ.get('CREDIT_COST_PREMIUM') or 3)
    
    # Gemini AI configuration
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or 'sqlite:///app.db'

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    
    # Production Redis configuration (Cloud Memorystore)
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', REDIS_URL)
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', REDIS_URL)
    
    # Celery configuration for production
    CELERY_TASK_ALWAYS_EAGER = False
    CELERY_TASK_EAGER_PROPAGATES = True
    CELERY_WORKER_CONCURRENCY = int(os.environ.get('CELERY_WORKER_CONCURRENCY', '4'))
    CELERY_WORKER_MAX_TASKS_PER_CHILD = int(os.environ.get('CELERY_WORKER_MAX_TASKS_PER_CHILD', '1000'))
    
    # Cloud SQL configuration
    CLOUD_SQL_CONNECTION_NAME = os.environ.get('CLOUD_SQL_CONNECTION_NAME')
    
    # SQLAlchemy connection pooling for Cloud Run
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 5,
        'pool_recycle': 3600,  # Recycle connections after 1 hour
        'pool_pre_ping': True,  # Verify connections before use
        'pool_timeout': 20,     # Wait up to 20 seconds for a connection
        'max_overflow': 10,     # Allow up to 10 additional connections
        'echo': False
    }
    
    @classmethod
    def init_app(cls, app):
        # Production-specific initialization
        pass

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
} 