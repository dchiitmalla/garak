#!/usr/bin/env python3
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
