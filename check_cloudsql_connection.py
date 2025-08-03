#!/usr/bin/env python3
"""
Check Cloud SQL Connection Script

This script helps diagnose and set up Cloud SQL connection.
"""

import os
import sys

def check_cloudsql_setup():
    """Check Cloud SQL setup and provide guidance"""
    print("☁️ ===== CLOUD SQL CONNECTION DIAGNOSTIC =====")
    print()
    
    # Check current environment variables
    print("🌍 ===== CURRENT ENVIRONMENT VARIABLES =====")
    database_url = os.environ.get('DATABASE_URL')
    print(f"DATABASE_URL: {database_url if database_url else 'Not set'}")
    
    # Check for other potential database variables
    other_db_vars = [
        'CLOUD_SQL_CONNECTION_NAME',
        'DB_HOST',
        'DB_PORT', 
        'DB_NAME',
        'DB_USER',
        'DB_PASSWORD',
        'GOOGLE_CLOUD_PROJECT'
    ]
    
    for var in other_db_vars:
        value = os.environ.get(var)
        if value:
            print(f"{var}: {value}")
        else:
            print(f"{var}: Not set")
    print()
    
    # Check if we're in a production environment
    print("🏭 ===== ENVIRONMENT CHECK =====")
    flask_env = os.environ.get('FLASK_ENV', 'Not set')
    print(f"FLASK_ENV: {flask_env}")
    
    if flask_env == 'production':
        print("✅ Running in production mode")
    else:
        print("⚠️ Not in production mode - this might affect database connection")
    print()
    
    # Provide guidance
    print("💡 ===== CLOUD SQL SETUP GUIDANCE =====")
    print()
    
    if not database_url:
        print("❌ DATABASE_URL is not set")
        print()
        print("To connect to Cloud SQL, you need to set DATABASE_URL:")
        print()
        print("For PostgreSQL:")
        print("export DATABASE_URL='postgresql://username:password@host:port/database'")
        print()
        print("For MySQL:")
        print("export DATABASE_URL='mysql://username:password@host:port/database'")
        print()
        print("Example Cloud SQL connection string:")
        print("export DATABASE_URL='postgresql://prompttovideo:password@34.123.45.67:5432/prompttovideo'")
        print()
        print("Or if using Cloud SQL Proxy:")
        print("export DATABASE_URL='postgresql://prompttovideo:password@localhost:5432/prompttovideo'")
        print()
    else:
        print("✅ DATABASE_URL is set")
        if 'localhost' in database_url:
            print("ℹ️ Using localhost - you might be using Cloud SQL Proxy")
        elif '34.' in database_url or '35.' in database_url:
            print("ℹ️ Using direct Cloud SQL connection")
        else:
            print("ℹ️ Using custom database connection")
        print()
    
    print("🔧 ===== NEXT STEPS =====")
    print("1. Set DATABASE_URL to your Cloud SQL connection string")
    print("2. Make sure Cloud SQL instance is running")
    print("3. Verify network connectivity")
    print("4. Run the search script again")
    print()
    
    print("📋 ===== COMMON CLOUD SQL ISSUES =====")
    print("• Connection timeout: Check if Cloud SQL instance is running")
    print("• Authentication failed: Verify username/password")
    print("• Network error: Check firewall rules and IP whitelist")
    print("• Proxy not running: Start Cloud SQL Proxy if using it")
    print()

if __name__ == "__main__":
    check_cloudsql_setup() 