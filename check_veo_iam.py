#!/usr/bin/env python3
"""
Check if the service account has proper IAM roles for Veo API
"""

import os
import subprocess
import json
import sys

def check_gcloud_available():
    """Check if gcloud command is available"""
    print("🔍 Checking if gcloud is available...")
    
    try:
        result = subprocess.run(['gcloud', '--version'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ gcloud is available")
            return True
        else:
            print("❌ gcloud command failed")
            return False
    except FileNotFoundError:
        print("❌ gcloud command not found in PATH")
        return False
    except Exception as e:
        print(f"❌ Error checking gcloud: {e}")
        return False

def check_service_account_roles():
    """Check if the service account has the required IAM roles"""
    print("🔍 Checking Service Account IAM Roles for Veo API")
    print("=" * 60)
    
    # Get project ID
    project_id = os.environ.get('GOOGLE_CLOUD_PROJECT_ID', 'dirly-466300')
    print(f"📋 Project ID: {project_id}")
    
    # Get service account email
    service_account = "1032601070049-compute@developer.gserviceaccount.com"
    print(f"👤 Service Account: {service_account}")
    
    # Required roles for Veo API
    required_roles = [
        "roles/aiplatform.user",
        "roles/aiplatform.developer", 
        "roles/storage.objectViewer",
        "roles/storage.objectCreator"
    ]
    
    print(f"\n🔑 Required IAM Roles for Veo API:")
    for role in required_roles:
        print(f"   - {role}")
    
    print(f"\n🔍 Checking current roles...")
    
    if not check_gcloud_available():
        print("\n⚠️ gcloud not available - cannot check IAM roles automatically")
        print("🔧 Please check IAM roles manually in Google Cloud Console:")
        print(f"   https://console.cloud.google.com/iam-admin/iam?project={project_id}")
        print("\n📋 Required roles for the service account:")
        for role in required_roles:
            print(f"   - {role}")
        return False
    
    try:
        # Get current IAM policy for the service account
        cmd = [
            'gcloud', 'projects', 'get-iam-policy', project_id,
            '--flatten=bindings[].members',
            f'--filter=bindings.members:{service_account}',
            '--format=json'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            policy_data = json.loads(result.stdout)
            
            if not policy_data:
                print(f"❌ No IAM bindings found for service account: {service_account}")
                print(f"🔧 Please add the required roles in Google Cloud Console:")
                print(f"   https://console.cloud.google.com/iam-admin/iam?project={project_id}")
                return False
            
            print(f"✅ Found IAM bindings for service account")
            
            # Extract roles
            current_roles = []
            for binding in policy_data:
                if 'bindings' in binding:
                    for role_binding in binding['bindings']:
                        if 'role' in role_binding:
                            current_roles.append(role_binding['role'])
            
            print(f"\n📋 Current roles:")
            for role in current_roles:
                print(f"   ✅ {role}")
            
            # Check if required roles are present
            missing_roles = []
            for required_role in required_roles:
                if required_role not in current_roles:
                    missing_roles.append(required_role)
            
            if missing_roles:
                print(f"\n❌ Missing required roles:")
                for role in missing_roles:
                    print(f"   ❌ {role}")
                
                print(f"\n🔧 To fix, run these commands:")
                for role in missing_roles:
                    print(f"   gcloud projects add-iam-policy-binding {project_id} \\")
                    print(f"     --member=serviceAccount:{service_account} \\")
                    print(f"     --role={role}")
                
                return False
            else:
                print(f"\n✅ All required roles are present!")
                return True
                
        else:
            print(f"❌ Failed to get IAM policy: {result.stderr}")
            print(f"🔧 Please check IAM roles manually in Google Cloud Console:")
            print(f"   https://console.cloud.google.com/iam-admin/iam?project={project_id}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Command timed out")
        return False
    except Exception as e:
        print(f"❌ Error checking IAM roles: {e}")
        return False

def check_veo_api_enabled():
    """Check if Veo API is enabled"""
    print(f"\n🔍 Checking if Veo API is enabled...")
    
    project_id = os.environ.get('GOOGLE_CLOUD_PROJECT_ID', 'dirly-466300')
    
    if not check_gcloud_available():
        print("⚠️ gcloud not available - cannot check API status automatically")
        print("🔧 Please check if Vertex AI API is enabled manually:")
        print(f"   https://console.cloud.google.com/apis/library/aiplatform.googleapis.com?project={project_id}")
        return False
    
    try:
        # Check if Vertex AI API is enabled (which includes Veo)
        cmd = [
            'gcloud', 'services', 'list', '--enabled',
            '--filter=name:aiplatform.googleapis.com',
            '--format=json'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            services = json.loads(result.stdout)
            
            if services:
                print("✅ Vertex AI API is enabled")
                return True
            else:
                print("❌ Vertex AI API is not enabled")
                print(f"🔧 To enable, run:")
                print(f"   gcloud services enable aiplatform.googleapis.com --project={project_id}")
                print(f"   Or enable manually: https://console.cloud.google.com/apis/library/aiplatform.googleapis.com?project={project_id}")
                return False
                
        else:
            print(f"❌ Failed to check API status: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error checking API status: {e}")
        return False

def provide_manual_instructions():
    """Provide manual instructions for setting up Veo API"""
    print("\n📋 Manual Setup Instructions")
    print("=" * 60)
    
    project_id = os.environ.get('GOOGLE_CLOUD_PROJECT_ID', 'dirly-466300')
    service_account = "1032601070049-compute@developer.gserviceaccount.com"
    
    print("1. Enable Vertex AI API:")
    print(f"   - Go to: https://console.cloud.google.com/apis/library/aiplatform.googleapis.com?project={project_id}")
    print(f"   - Click 'Enable'")
    print(f"   - Or run: gcloud services enable aiplatform.googleapis.com --project={project_id}")
    
    print("\n2. Add IAM roles to service account:")
    print(f"   - Go to: https://console.cloud.google.com/iam-admin/iam?project={project_id}")
    print(f"   - Find service account: {service_account}")
    print(f"   - Click the edit (pencil) icon")
    print(f"   - Add these roles:")
    print(f"     * AI Platform Developer")
    print(f"     * AI Platform User")
    print(f"     * Storage Object Viewer")
    print(f"     * Storage Object Creator")
    
    print("\n3. Or run these commands:")
    roles = [
        "roles/aiplatform.user",
        "roles/aiplatform.developer", 
        "roles/storage.objectViewer",
        "roles/storage.objectCreator"
    ]
    for role in roles:
        print(f"   gcloud projects add-iam-policy-binding {project_id} \\")
        print(f"     --member=serviceAccount:{service_account} \\")
        print(f"     --role={role}")

def main():
    """Main function"""
    print("🚀 Veo API IAM Role Check")
    print("=" * 60)
    
    # Check if Veo API is enabled
    api_enabled = check_veo_api_enabled()
    
    if api_enabled:
        # Check IAM roles
        roles_ok = check_service_account_roles()
        
        if roles_ok:
            print(f"\n🎉 All checks passed! Veo API should work correctly.")
        else:
            print(f"\n⚠️ IAM roles need to be configured.")
            provide_manual_instructions()
    else:
        print(f"\n❌ Veo API needs to be enabled.")
        provide_manual_instructions()
    
    print(f"\n" + "=" * 60)

if __name__ == "__main__":
    main() 