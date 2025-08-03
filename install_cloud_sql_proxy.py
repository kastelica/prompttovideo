#!/usr/bin/env python3
"""
Install Cloud SQL Proxy Script for Windows

This script helps install Cloud SQL Proxy on Windows for connecting to Cloud SQL.
"""

import os
import sys
import subprocess
import urllib.request
import zipfile
import shutil
import time

def download_cloud_sql_proxy():
    """Download Cloud SQL Proxy for Windows"""
    print("📥 ===== DOWNLOADING CLOUD SQL PROXY =====")
    
    # Cloud SQL Proxy download URL for Windows
    url = "https://dl.google.com/cloudsql/cloud_sql_proxy_x64.exe"
    filename = "cloud_sql_proxy.exe"
    
    try:
        print(f"Downloading from: {url}")
        urllib.request.urlretrieve(url, filename)
        print(f"✅ Downloaded: {filename}")
        return filename
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return None

def install_to_path():
    """Install Cloud SQL Proxy to PATH"""
    print("🔧 ===== INSTALLING TO PATH =====")
    
    # Check if already installed
    try:
        result = subprocess.run(['cloud_sql_proxy', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ Cloud SQL Proxy is already installed and in PATH")
            return True
    except:
        pass
    
    # Download if not exists
    if not os.path.exists("cloud_sql_proxy.exe"):
        filename = download_cloud_sql_proxy()
        if not filename:
            return False
    else:
        filename = "cloud_sql_proxy.exe"
    
    # Try to install to a directory in PATH
    install_dirs = [
        os.path.join(os.environ.get('USERPROFILE', ''), 'AppData', 'Local', 'Microsoft', 'WinGet', 'Packages'),
        os.path.join(os.environ.get('PROGRAMFILES', ''), 'Google', 'Cloud SDK'),
        os.path.join(os.environ.get('USERPROFILE', ''), 'bin'),
        os.path.join(os.environ.get('PROGRAMFILES', ''), 'cloud_sql_proxy')
    ]
    
    for install_dir in install_dirs:
        if os.path.exists(install_dir) or install_dir == install_dirs[-1]:
            try:
                os.makedirs(install_dir, exist_ok=True)
                target_path = os.path.join(install_dir, "cloud_sql_proxy.exe")
                shutil.copy2(filename, target_path)
                print(f"✅ Installed to: {target_path}")
                
                # Add to PATH if not already there
                current_path = os.environ.get('PATH', '')
                if install_dir not in current_path:
                    print(f"💡 Add this to your PATH: {install_dir}")
                    print("   Or restart your terminal and try again")
                
                return True
            except Exception as e:
                print(f"❌ Failed to install to {install_dir}: {e}")
                continue
    
    return False

def test_installation():
    """Test if Cloud SQL Proxy is working"""
    print("🧪 ===== TESTING INSTALLATION =====")
    
    try:
        result = subprocess.run(['cloud_sql_proxy', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Cloud SQL Proxy is working!")
            print(f"Version: {result.stdout.strip()}")
            return True
        else:
            print("❌ Cloud SQL Proxy is not working properly")
            print(f"Error: {result.stderr}")
            return False
    except FileNotFoundError:
        print("❌ Cloud SQL Proxy not found in PATH")
        return False
    except subprocess.TimeoutExpired:
        print("❌ Cloud SQL Proxy command timed out")
        return False

def main():
    """Main installation function"""
    print("☁️ ===== CLOUD SQL PROXY INSTALLER =====")
    print()
    
    print("This script will install Cloud SQL Proxy for Windows")
    print("Cloud SQL Proxy allows you to connect to Cloud SQL from your local machine")
    print()
    
    # Check if already installed
    if test_installation():
        print("🎉 Cloud SQL Proxy is already installed and working!")
        return True
    
    # Install Cloud SQL Proxy
    print("📦 ===== INSTALLING CLOUD SQL PROXY =====")
    if install_to_path():
        print("⏳ Testing installation...")
        time.sleep(2)
        
        if test_installation():
            print("🎉 Installation successful!")
            print()
            print("📋 ===== NEXT STEPS =====")
            print("1. Restart your terminal/PowerShell")
            print("2. Run: python connect_production_db.py")
            print("3. The proxy will connect you to your production database")
            return True
        else:
            print("❌ Installation completed but testing failed")
            print("Try restarting your terminal and running the test again")
            return False
    else:
        print("❌ Installation failed")
        print()
        print("🔧 ===== MANUAL INSTALLATION =====")
        print("1. Download from: https://cloud.google.com/sql/docs/postgres/connect-admin-proxy")
        print("2. Extract to a directory in your PATH")
        print("3. Or add the directory to your PATH environment variable")
        return False

if __name__ == "__main__":
    main() 