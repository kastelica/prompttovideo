#!/usr/bin/env python3
"""
Initialize the database for local development
"""
from app import create_app, db
from app.models import User, Video, CreditTransaction, PromptPack, AdminUser

def init_database():
    app = create_app('development')
    with app.app_context():
        # Create all tables
        db.create_all()
        print("Database tables created successfully!")
        
        # Create a sample admin user if none exists
        admin = AdminUser.query.filter_by(email='admin@prompttovideo.com').first()
        if not admin:
            admin = AdminUser(
                email='admin@prompttovideo.com',
                password_hash='admin123',  # In production, use proper password hashing
                role='super_admin'
            )
            db.session.add(admin)
            db.session.commit()
            print("Admin user created: admin@prompttovideo.com")
        
        print("Database initialization complete!")

if __name__ == '__main__':
    init_database() 