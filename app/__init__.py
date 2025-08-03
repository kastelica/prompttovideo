import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_cors import CORS
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
import sqlalchemy as sa

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, continue without it

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()

def create_app(config_name=None):
    app = Flask(__name__)
    
    # Load configuration
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app.config.from_object(f'config.{config_name.capitalize()}Config')
    
    # Initialize Sentry
    if app.config.get('SENTRY_DSN'):
        sentry_sdk.init(
            dsn=app.config['SENTRY_DSN'],
            integrations=[FlaskIntegration()],
            traces_sample_rate=1.0,
            environment=config_name
        )
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    CORS(app)
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))
    
    # Import models to ensure they are registered with SQLAlchemy
    from app import models
    
    # Celery removed - using background threads instead
    
    # Register blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    from app.payments import bp as payments_bp
    app.register_blueprint(payments_bp, url_prefix='/payments')
    
    from app.main.referral_routes import bp as referral_bp
    app.register_blueprint(referral_bp)
    
    from app.api.developer_routes import bp as developer_bp
    app.register_blueprint(developer_bp)
    
    # Initialize database and ensure required columns exist
    with app.app_context():
        init_database(app)
    
    return app

def init_database(app):
    """Initialize database and ensure required columns exist"""
    try:
        # Create all tables
        db.create_all()
        
        # Check if email_verification_expires column exists
        inspector = sa.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('users')]
        
        if 'email_verification_expires' not in columns:
            app.logger.info("Adding email_verification_expires column to users table...")
            with db.engine.begin() as conn:
                conn.execute(sa.text('ALTER TABLE users ADD COLUMN email_verification_expires DATETIME'))
            app.logger.info("email_verification_expires column added successfully")
        else:
            app.logger.info("email_verification_expires column already exists")
            
    except Exception as e:
        app.logger.error(f"Database initialization error: {e}")
        # Don't fail the app startup, just log the error 