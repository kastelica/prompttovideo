#!/usr/bin/env python3
"""
Test Database Connection Script

This script tests the connection to the production Cloud SQL database.
"""

import os
import subprocess
import time
from sqlalchemy import create_engine, text

def test_connection():
    """Test database connection with different methods"""
    print("🔍 ===== TESTING DATABASE CONNECTION =====")
    
    # Test 1: Direct connection (if IP is whitelisted)
    print("\n🌐 ===== TEST 1: DIRECT CONNECTION =====")
    direct_url = "postgresql://prompttovideo:PromptToVideo2024!@34.46.33.136:5432/prompttovideo"
    
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
    
    # Test 2: Proxy connection
    print("\n🔌 ===== TEST 2: PROXY CONNECTION =====")
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
    
    # Test 3: Check if proxy is running
    print("\n🔍 ===== TEST 3: CHECKING PROXY STATUS =====")
    try:
        result = subprocess.run(['netstat', '-an'], capture_output=True, text=True)
        if ':5432' in result.stdout:
            print("✅ Port 5432 is in use")
            print("Proxy might be running but connection failed")
        else:
            print("❌ Port 5432 is not in use")
            print("Cloud SQL Proxy is not running")
    except Exception as e:
        print(f"❌ Could not check port status: {e}")
    
    return False

def start_proxy():
    """Start Cloud SQL Proxy"""
    print("\n🚀 ===== STARTING CLOUD SQL PROXY =====")
    
    connection_name = "dirly-466300:us-central1:prompttovideo-db"
    
    try:
        proxy_cmd = [
            'cloud_sql_proxy',
            f'--instances={connection_name}',
            '--port=5432'
        ]
        
        print(f"Starting proxy for: {connection_name}")
        
        # Start in background
        if os.name == 'nt':
            subprocess.Popen(['start', '/B'] + proxy_cmd, shell=True)
        else:
            subprocess.Popen(proxy_cmd)
        
        print("⏳ Waiting for proxy to start...")
        time.sleep(5)
        return True
        
    except Exception as e:
        print(f"❌ Failed to start Cloud SQL Proxy: {e}")
        return False

def main():
    """Main function"""
    print("☁️ ===== DATABASE CONNECTION TESTER =====")
    print()
    
    # First try direct connection
    if test_connection():
        print("\n🎉 Connection successful!")
        return
    
    # If direct connection fails, try starting proxy
    print("\n🔧 ===== TRYING WITH PROXY =====")
    if start_proxy():
        print("⏳ Testing connection with proxy...")
        time.sleep(3)
        
        if test_connection():
            print("\n🎉 Connection successful with proxy!")
            return
    
    # If all fails, provide troubleshooting info
    print("\n❌ ===== CONNECTION FAILED =====")
    print("\n🔧 ===== TROUBLESHOOTING =====")
    print("1. Check if Cloud SQL instance is running")
    print("2. Verify your IP is whitelisted in Cloud SQL")
    print("3. Make sure Cloud SQL Proxy is installed")
    print("4. Check if credentials are correct")
    print("5. Try running: cloud_sql_proxy --instances=dirly-466300:us-central1:prompttovideo-db --port=5432")

if __name__ == "__main__":
    main() 