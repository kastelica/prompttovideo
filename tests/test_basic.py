import pytest
from app import create_app, db
from app.models import User

def test_app_creation():
    """Test that the Flask app can be created"""
    app = create_app('testing')
    assert app is not None
    assert app.config['TESTING'] == True

def test_database_connection():
    """Test that the database can be connected to and tables created"""
    app = create_app('testing')
    with app.app_context():
        # Ensure models are imported
        from app import models
        
        # Check what tables SQLAlchemy knows about
        print(f"SQLAlchemy metadata tables: {list(db.metadata.tables.keys())}")
        
        # Create all tables
        db.create_all()
        
        # Verify tables were created by checking if we can query them
        try:
            # This should work if tables exist
            db.session.execute(db.text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = [row[0] for row in db.session.execute(db.text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()]
            print(f"Created tables: {tables}")
            
            # Try to create a simple user
            user = User(email='test@example.com')
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
            
            # Verify the user was created
            retrieved_user = User.query.filter_by(email='test@example.com').first()
            assert retrieved_user is not None
            assert retrieved_user.email == 'test@example.com'
            
            # Clean up
            db.session.delete(user)
            db.session.commit()
            
        except Exception as e:
            print(f"Error: {e}")
            raise
        
        finally:
            db.drop_all()

def test_user_model():
    """Test the User model functionality"""
    app = create_app('testing')
    with app.app_context():
        # Ensure models are imported
        from app import models
        
        db.create_all()
        
        user = User(email='test@example.com')
        user.set_password('password123')
        user.email_verified = True
        db.session.add(user)
        db.session.commit()
        
        # Test password verification
        assert user.check_password('password123') == True
        assert user.check_password('wrongpassword') == False
        
        # Test credit management
        user.add_credits(10, 'test')
        db.session.commit()
        assert user.credits == 10
        
        # Test that credits were added correctly
        retrieved_user = User.query.filter_by(email='test@example.com').first()
        assert retrieved_user.credits == 10
        
        # Just drop all tables to clean up - this avoids the relationship issue
        db.drop_all() 