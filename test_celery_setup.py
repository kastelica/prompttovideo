#!/usr/bin/env python3
"""
Test script to verify Celery setup is working
"""

import os
import sys

# Set environment variables
os.environ['REDIS_URL'] = 'redis://localhost:6379/0'
os.environ['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
os.environ['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'

def test_celery_import():
    """Test if Celery can be imported and configured"""
    try:
        from app.tasks import celery, get_celery_task
        print("✅ Celery imported successfully")
        
        # Test if we can get the task
        task = get_celery_task()
        if task:
            print("✅ Celery task created successfully")
            return True
        else:
            print("❌ Celery task not available")
            return False
            
    except Exception as e:
        print(f"❌ Celery import failed: {e}")
        return False

def test_redis_connection():
    """Test Redis connection"""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✅ Redis connection successful")
        return True
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False

def test_celery_worker():
    """Test if Celery worker can be started"""
    try:
        import subprocess
        import time
        
        print("🔄 Starting Celery worker test...")
        
        # Start worker in background
        process = subprocess.Popen([
            sys.executable, '-m', 'celery', '-A', 'app.tasks.celery', 
            'worker', '--loglevel=info', '--pool=solo'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a moment for worker to start
        time.sleep(3)
        
        # Check if process is still running
        if process.poll() is None:
            print("✅ Celery worker started successfully")
            process.terminate()
            return True
        else:
            stdout, stderr = process.communicate()
            print(f"❌ Celery worker failed to start")
            print(f"STDOUT: {stdout.decode()}")
            print(f"STDERR: {stderr.decode()}")
            return False
            
    except Exception as e:
        print(f"❌ Celery worker test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Celery Setup Test")
    print("=" * 40)
    
    # Test Redis
    redis_ok = test_redis_connection()
    
    # Test Celery import
    celery_import_ok = test_celery_import()
    
    # Test Celery worker
    worker_ok = test_celery_worker()
    
    print("\n" + "=" * 40)
    print("📊 Test Results:")
    print(f"   Redis: {'✅' if redis_ok else '❌'}")
    print(f"   Celery Import: {'✅' if celery_import_ok else '❌'}")
    print(f"   Celery Worker: {'✅' if worker_ok else '❌'}")
    
    if redis_ok and celery_import_ok and worker_ok:
        print("\n🎉 SUCCESS: Celery setup is working!")
        print("📝 You can now use asynchronous video generation")
    else:
        print("\n⚠️  Some tests failed. Check the output above.")
    
    print("\n" + "=" * 40)
    print("�� Test complete!") 