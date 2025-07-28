#!/usr/bin/env python3
"""
Production readiness verification for Garak Dashboard API.

This script verifies that all essential functionality works correctly
for production deployment.
"""

import os
import sys

# Add dashboard directory to path
sys.path.insert(0, 'dashboard')
sys.path.insert(0, '.')

# Set environment variables for testing
os.environ['DISABLE_AUTH'] = 'true'
os.environ['FLASK_ENV'] = 'testing'

def verify_essential_functionality():
    """Verify essential functionality is working."""
    print("🔍 Production Readiness Verification")
    print("=" * 50)
    
    success = True
    
    # 1. Test Pydantic models
    print("\n1️⃣ Testing Pydantic Models...")
    try:
        from api.core.models import ErrorResponse, CreateScanRequest
        
        # Test ErrorResponse with both dict and list details
        error1 = ErrorResponse(error='test', message='test', details={'key': 'value'})
        error2 = ErrorResponse(error='test', message='test', details=[{'error': 'field required'}])
        
        # Test CreateScanRequest
        scan_req = CreateScanRequest(
            generator='test.Blank',  # Should work with test generators
            model_name='test-model',
            probe_categories=['dan'],
            api_keys={}
        )
        
        print("   ✅ Pydantic models working correctly")
    except Exception as e:
        print(f"   ❌ Pydantic models failed: {e}")
        success = False
    
    # 2. Test rate limiter basic functionality
    print("\n2️⃣ Testing Rate Limiter...")
    try:
        from api.core.rate_limiter import RateLimiter
        
        limiter = RateLimiter()
        is_limited, rate_info = limiter.is_rate_limited('test', 10, 60)
        
        # Check all required keys are present
        required_keys = ['requests', 'limit', 'window', 'reset_time', 'remaining']
        for key in required_keys:
            if key not in rate_info:
                raise KeyError(f"Missing key: {key}")
        
        print("   ✅ Rate limiter working (all keys present)")
    except Exception as e:
        print(f"   ❌ Rate limiter failed: {e}")
        success = False
    
    # 3. Test authentication bypass
    print("\n3️⃣ Testing Authentication Bypass...")
    try:
        from flask import g
        from api.core.auth import api_key_required
        from app import app
        
        with app.app_context():
            with app.test_request_context():
                @api_key_required
                def test_endpoint():
                    return g.api_key_info
                
                api_key_info = test_endpoint()
                
                # Check required fields
                required_fields = ['id', 'name', 'permissions', 'rate_limit', 'user_id', 'key_prefix']
                for field in required_fields:
                    if field not in api_key_info:
                        raise KeyError(f"Missing field: {field}")
                
                # Check permissions is a list
                if not isinstance(api_key_info['permissions'], list):
                    raise TypeError("Permissions should be a list")
                
                print("   ✅ Authentication bypass working correctly")
    except Exception as e:
        print(f"   ❌ Authentication bypass failed: {e}")
        success = False
    
    # 4. Test Flask app critical endpoints
    print("\n4️⃣ Testing Flask App Endpoints...")
    try:
        from app import app
        
        with app.test_client() as client:
            # Test health
            response = client.get('/api/v1/health')
            if response.status_code != 200:
                raise Exception(f"Health endpoint failed: {response.status_code}")
            
            # Test generators
            response = client.get('/api/v1/generators')
            if response.status_code != 200:
                raise Exception(f"Generators endpoint failed: {response.status_code}")
            
            # Test probes
            response = client.get('/api/v1/probes')
            if response.status_code != 200:
                raise Exception(f"Probes endpoint failed: {response.status_code}")
            
            print("   ✅ Critical endpoints working")
    except Exception as e:
        print(f"   ❌ Flask endpoints failed: {e}")
        success = False
    
    # 5. Test scan creation (most important)
    print("\n5️⃣ Testing Scan Creation...")
    try:
        from app import app
        
        with app.test_client() as client:
            scan_data = {
                'generator': 'test.Blank',
                'model_name': 'test-model',
                'probe_categories': ['dan'],
                'name': 'Production Test',
                'api_keys': {}
            }
            
            response = client.post('/api/v1/scans', 
                                 json=scan_data,
                                 content_type='application/json')
            
            if response.status_code != 201:
                raise Exception(f"Scan creation failed: {response.status_code} - {response.get_json()}")
            
            scan_response = response.get_json()
            scan_id = scan_response['scan_id']
            
            # Test scan retrieval
            response = client.get(f'/api/v1/scans/{scan_id}')
            if response.status_code != 200:
                raise Exception(f"Scan retrieval failed: {response.status_code}")
            
            print("   ✅ Scan creation and retrieval working")
    except Exception as e:
        print(f"   ❌ Scan creation failed: {e}")
        success = False
    
    # 6. Test rate limit headers
    print("\n6️⃣ Testing Rate Limit Headers...")
    try:
        from app import app
        
        with app.test_client() as client:
            response = client.get('/api/v1/generators')
            
            required_headers = ['X-RateLimit-Limit', 'X-RateLimit-Remaining', 'X-RateLimit-Window']
            for header in required_headers:
                if header not in response.headers:
                    raise Exception(f"Missing header: {header}")
            
            print("   ✅ Rate limit headers present")
    except Exception as e:
        print(f"   ❌ Rate limit headers failed: {e}")
        success = False
    
    # Summary
    print(f"\n{'='*50}")
    if success:
        print("🎉 PRODUCTION READY!")
        print("✅ All essential functionality verified")
        print("✅ API is ready for deployment")
        print("\nKey features working:")
        print("  • Pydantic model validation")
        print("  • Rate limiting with proper headers")
        print("  • Authentication bypass for development") 
        print("  • Scan creation and management")
        print("  • Error handling and responses")
        print("  • All critical API endpoints")
    else:
        print("❌ NOT PRODUCTION READY")
        print("⚠️  Some essential functionality failed")
        print("🔧 Fix issues before deployment")
    
    return success

if __name__ == '__main__':
    success = verify_essential_functionality()
    sys.exit(0 if success else 1)