#!/usr/bin/env python3
"""
Connect to Production Database Script

This script helps connect to the production Cloud SQL database from local development.
Supports both Cloud SQL Proxy and direct connection methods.
"""

import os
import sys
import subprocess
import time
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

def check_cloud_sql_proxy():
    """Check if Cloud SQL Proxy is installed and running"""
    print("🔍 ===== CHECKING CLOUD SQL PROXY =====")
    
    # Check if cloud_sql_proxy is installed
    try:
        result = subprocess.run(['cloud_sql_proxy', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ Cloud SQL Proxy is installed")
            print(f"Version: {result.stdout.strip()}")
            return True
        else:
            print("❌ Cloud SQL Proxy is not working properly")
            return False
    except FileNotFoundError:
        print("❌ Cloud SQL Proxy is not installed")
        return False
    except subprocess.TimeoutExpired:
        print("❌ Cloud SQL Proxy command timed out")
        return False

def start_cloud_sql_proxy():
    """Start Cloud SQL Proxy for local connection"""
    print("🚀 ===== STARTING CLOUD SQL PROXY =====")
    
    connection_name = "dirly-466300:us-central1:prompttovideo-db"
    
    # Check if proxy is already running
    try:
        result = subprocess.run(['netstat', '-an'], capture_output=True, text=True)
        if ':5432' in result.stdout:
            print("✅ Port 5432 is already in use - proxy might be running")
            return True
    except:
        pass
    
    print(f"Starting Cloud SQL Proxy for: {connection_name}")
    print("This will run in the background...")
    
    try:
        # Start proxy in background
        proxy_cmd = [
            'cloud_sql_proxy',
            f'--instances={connection_name}',
            '--port=5432'
        ]
        
        # On Windows, use start to run in background
        if os.name == 'nt':
            subprocess.Popen(['start', '/B'] + proxy_cmd, shell=True)
        else:
            subprocess.Popen(proxy_cmd)
        
        print("⏳ Waiting for proxy to start...")
        time.sleep(3)
        return True
        
    except Exception as e:
        print(f"❌ Failed to start Cloud SQL Proxy: {e}")
        return False

def test_direct_connection():
    """Test direct connection to Cloud SQL (requires IP whitelist)"""
    print("🌐 ===== TESTING DIRECT CONNECTION =====")
    
    # You'll need to get your public IP and whitelist it in Cloud SQL
    direct_url = "postgresql://prompttovideo:PromptToVideo2024!@34.123.45.67:5432/prompttovideo"
    
    try:
        engine = create_engine(direct_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print("✅ Direct connection successful!")
            print(f"Database version: {version}")
            return True
    except Exception as e:
        print(f"❌ Direct connection failed: {e}")
        print("This might be because your IP is not whitelisted in Cloud SQL")
        return False

def test_proxy_connection():
    """Test connection through Cloud SQL Proxy"""
    print("🔌 ===== TESTING PROXY CONNECTION =====")
    
    proxy_url = "postgresql://prompttovideo:PromptToVideo2024!@localhost:5432/prompttovideo"
    
    try:
        engine = create_engine(proxy_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print("✅ Proxy connection successful!")
            print(f"Database version: {version}")
            return True
    except Exception as e:
        print(f"❌ Proxy connection failed: {e}")
        return False

def get_public_ip():
    """Get the current public IP address"""
    print("🌍 ===== GETTING PUBLIC IP =====")
    
    try:
        import requests
        response = requests.get('https://api.ipify.org', timeout=5)
        ip = response.text
        print(f"Your public IP: {ip}")
        return ip
    except Exception as e:
        print(f"❌ Could not get public IP: {e}")
        return None

def main():
    """Main function to handle database connection"""
    print("☁️ ===== CONNECTING TO PRODUCTION DATABASE =====")
    print()
    
    # Check environment
    print("🔧 ===== ENVIRONMENT SETUP =====")
    flask_env = os.environ.get('FLASK_ENV', 'Not set')
    print(f"FLASK_ENV: {flask_env}")
    
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        print(f"DATABASE_URL: {database_url}")
    else:
        print("DATABASE_URL: Not set")
    
    gcs_bucket = os.environ.get('GCS_BUCKET_NAME')
    print(f"GCS_BUCKET_NAME: {gcs_bucket}")
    
    project_id = os.environ.get('GOOGLE_CLOUD_PROJECT_ID')
    print(f"GOOGLE_CLOUD_PROJECT_ID: {project_id}")
    print()
    
    # Get public IP for whitelisting
    public_ip = get_public_ip()
    if public_ip:
        print("💡 To enable direct connection, whitelist this IP in Cloud SQL:")
        print(f"   {public_ip}")
        print()
    
    # Try different connection methods
    print("🔌 ===== CONNECTION METHODS =====")
    print("1. Cloud SQL Proxy (recommended for local development)")
    print("2. Direct connection (requires IP whitelist)")
    print()
    
    # Check if Cloud SQL Proxy is available
    proxy_available = check_cloud_sql_proxy()
    
    if proxy_available:
        print("🚀 ===== USING CLOUD SQL PROXY =====")
        if start_cloud_sql_proxy():
            print("⏳ Waiting for proxy to be ready...")
            time.sleep(5)
            
            if test_proxy_connection():
                print("✅ Successfully connected via Cloud SQL Proxy!")
                print()
                print("📋 ===== NEXT STEPS =====")
                print("1. The proxy is now running on localhost:5432")
                print("2. You can connect using: postgresql://prompttovideo:PromptToVideo2024!@localhost:5432/prompttovideo")
                print("3. Keep this terminal open to maintain the connection")
                print("4. To stop the proxy, close this terminal or kill the process")
                return True
            else:
                print("❌ Proxy connection failed")
        else:
            print("❌ Failed to start Cloud SQL Proxy")
    
    # Try direct connection as fallback
    print("🌐 ===== TRYING DIRECT CONNECTION =====")
    if test_direct_connection():
        print("✅ Successfully connected directly!")
        return True
    
    # If both methods fail
    print("❌ ===== CONNECTION FAILED =====")
    print()
    print("🔧 ===== TROUBLESHOOTING =====")
    print("1. Install Cloud SQL Proxy:")
    print("   Download from: https://cloud.google.com/sql/docs/postgres/connect-admin-proxy")
    print()
    print("2. Or whitelist your IP in Cloud SQL:")
    print(f"   Add {public_ip} to authorized networks")
    print()
    print("3. Verify your credentials are correct")
    print("4. Make sure the Cloud SQL instance is running")
    
    return False

if __name__ == "__main__":
    main() 