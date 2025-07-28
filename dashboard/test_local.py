#!/usr/bin/env python3
"""
Local testing script for Garak Dashboard API.

This script provides comprehensive local error catching and testing
to identify issues before deployment.
"""

import os
import sys
import json
import requests
import traceback
from datetime import datetime

# Add dashboard directory to path
sys.path.insert(0, 'dashboard')
sys.path.insert(0, '.')

def test_imports():
    """Test all critical imports."""
    print("🧪 Testing imports...")
    
    try:
        from api.core.models import ErrorResponse, CreateScanRequest
        from api.core.auth import api_key_manager
        from api.core.rate_limiter import rate_limiter
        from api.core.utils import validate_json_request
        print("✅ All core imports successful")
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        traceback.print_exc()
        return False

def test_models():
    """Test Pydantic model validation."""
    print("\n🧪 Testing Pydantic models...")
    
    try:
        from api.core.models import ErrorResponse, CreateScanRequest
        
        # Test ErrorResponse
        error = ErrorResponse(error='test', message='test message')
        print(f"✅ ErrorResponse: {error.model_dump()}")
        
        # Test CreateScanRequest
        scan_request = CreateScanRequest(
            generator='test.Blank',
            model_name='test-model',
            probe_categories=['dan'],
            api_keys={}
        )
        print(f"✅ CreateScanRequest: {scan_request.model_dump()}")
        
        # Test invalid request
        try:
            invalid_request = CreateScanRequest(
                generator='invalid-generator',
                model_name='test-model'
            )
            print("❌ Should have failed validation")
            return False
        except Exception as e:
            print(f"✅ Validation correctly rejected invalid generator: {e}")
        
        return True
    except Exception as e:
        print(f"❌ Model error: {e}")
        traceback.print_exc()
        return False

def test_rate_limiter():
    """Test rate limiter functionality."""
    print("\n🧪 Testing rate limiter...")
    
    try:
        from api.core.rate_limiter import RateLimiter
        
        limiter = RateLimiter()
        
        # Test rate limiting
        is_limited, rate_info = limiter.is_rate_limited('test-key', 5, 60)
        print(f"✅ Rate limiter check: limited={is_limited}, info={rate_info}")
        
        # Verify 'remaining' key exists
        if 'remaining' not in rate_info:
            print("❌ Missing 'remaining' key in rate_info")
            return False
        
        print(f"✅ Rate info contains all required keys: {list(rate_info.keys())}")
        return True
    except Exception as e:
        print(f"❌ Rate limiter error: {e}")
        traceback.print_exc()
        return False

def test_flask_app():
    """Test Flask app startup."""
    print("\n🧪 Testing Flask app...")
    
    try:
        # Set environment variables for testing
        os.environ['DISABLE_AUTH'] = 'true'
        os.environ['FLASK_ENV'] = 'testing'
        
        from app import app
        
        with app.test_client() as client:
            # Test health endpoint
            response = client.get('/api/v1/health')
            print(f"✅ Health endpoint: {response.status_code}")
            
            if response.status_code == 200:
                data = response.get_json()
                print(f"   Status: {data.get('status')}")
            
            # Test generators endpoint
            response = client.get('/api/v1/generators')
            print(f"✅ Generators endpoint: {response.status_code}")
            
            # Test invalid scan creation (should return 400, not 500)
            response = client.post('/api/v1/scans', 
                                 json={'invalid': 'data'},
                                 content_type='application/json')
            print(f"✅ Invalid scan request: {response.status_code}")
            
            if response.status_code == 500:
                print("❌ Should return 400 for validation error, not 500")
                print(f"   Response: {response.get_json()}")
                return False
            
        return True
    except Exception as e:
        print(f"❌ Flask app error: {e}")
        traceback.print_exc()
        return False

def test_api_endpoints_locally():
    """Start local server and test endpoints."""
    print("\n🧪 Testing local API server...")
    
    import subprocess
    import time
    import threading
    
    def run_server():
        os.environ['DISABLE_AUTH'] = 'true'
        os.environ['PORT'] = '8001'
        try:
            subprocess.run(['python3', 'dashboard/app.py'], 
                         cwd='.', capture_output=True)
        except Exception as e:
            print(f"Server error: {e}")
    
    # Start server in background
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Wait for server to start
    time.sleep(3)
    
    try:
        base_url = 'http://localhost:8001'
        
        # Test health endpoint
        response = requests.get(f'{base_url}/api/v1/health', timeout=5)
        print(f"✅ Health endpoint: {response.status_code}")
        
        # Test generators endpoint
        response = requests.get(f'{base_url}/api/v1/generators', timeout=5)
        print(f"✅ Generators endpoint: {response.status_code}")
        
        # Test scan creation with test generator
        scan_data = {
            'generator': 'test.Blank',
            'model_name': 'test-model',
            'probe_categories': ['dan'],
            'probes': ['dan.Dan_11_0'],
            'api_keys': {}
        }
        response = requests.post(f'{base_url}/api/v1/scans', 
                               json=scan_data, timeout=10)
        print(f"✅ Scan creation: {response.status_code}")
        
        if response.status_code == 500:
            print(f"❌ Scan creation failed: {response.text}")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Local server test error: {e}")
        return False

def create_test_script():
    """Create a quick test script for common issues."""
    script_content = '''#!/usr/bin/env python3
"""Quick test for common API issues."""

import sys
sys.path.insert(0, 'dashboard')

def quick_test():
    try:
        # Test imports
        from api.core.models import ErrorResponse
        from api.core.rate_limiter import RateLimiter
        
        # Test ErrorResponse
        error = ErrorResponse(error='test', message='test')
        print(f"✅ ErrorResponse: {error.model_dump()}")
        
        # Test rate limiter
        limiter = RateLimiter()
        is_limited, rate_info = limiter.is_rate_limited('test', 10, 60)
        print(f"✅ Rate limiter: {rate_info}")
        
        # Check for 'remaining' key
        assert 'remaining' in rate_info, "Missing 'remaining' key"
        print("✅ All tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    quick_test()
'''
    
    with open('/Users/divyachitimalla/garak/dashboard/quick_test.py', 'w') as f:
        f.write(script_content)
    
    print("✅ Created dashboard/quick_test.py for rapid testing")

def main():
    """Run all tests."""
    print("🚀 Garak Dashboard Local Testing Suite")
    print("=" * 50)
    
    # Create test script
    create_test_script()
    
    tests = [
        ("Imports", test_imports),
        ("Models", test_models),
        ("Rate Limiter", test_rate_limiter),
        ("Flask App", test_flask_app),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*50}")
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:15} {status}")
        if result:
            passed += 1
    
    print(f"\n🏆 {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Ready for deployment.")
        return True
    else:
        print("⚠️  Some tests failed. Fix issues before deploying.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)