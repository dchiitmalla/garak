"""
Unit tests for rate limiter functionality.
"""

import pytest


class TestRateLimiter:
    """Test rate limiter functionality."""
    
    def test_rate_limiter_basic(self, rate_limiter):
        """Test basic rate limiter functionality."""
        # Test basic rate limiting (Redis may not be available)
        is_limited, rate_info = rate_limiter.is_rate_limited('test_key', 5, 60)
        
        # Verify all required keys are present
        required_keys = ['requests', 'limit', 'window', 'reset_time', 'remaining']
        for key in required_keys:
            assert key in rate_info, f"Missing key: {key}"
        
        # Verify values are correct types
        assert isinstance(rate_info['requests'], int)
        assert isinstance(rate_info['limit'], int)
        assert isinstance(rate_info['window'], int)
        assert isinstance(rate_info['remaining'], int)
        
        # Verify limits are logical
        assert rate_info['limit'] == 5
        assert rate_info['window'] == 60
        assert rate_info['remaining'] <= rate_info['limit']
        assert rate_info['remaining'] >= 0
    
    def test_rate_limiter_multiple_requests(self, rate_limiter):
        """Test multiple requests to rate limiter."""
        key = 'test_multi_key'
        limit = 5
        window = 60
        
        # Make multiple requests
        results = []
        for i in range(3):
            is_limited, rate_info = rate_limiter.is_rate_limited(key, limit, window)
            results.append((is_limited, rate_info))
        
        # All requests should have consistent structure
        for is_limited, rate_info in results:
            assert isinstance(is_limited, bool)
            assert isinstance(rate_info, dict)
            assert rate_info['limit'] == limit
            assert rate_info['window'] == window
    
    def test_rate_limiter_different_keys(self, rate_limiter):
        """Test rate limiter with different keys."""
        key1 = 'test_key_1'
        key2 = 'test_key_2'
        
        # Test with different keys
        is_limited1, rate_info1 = rate_limiter.is_rate_limited(key1, 5, 60)
        is_limited2, rate_info2 = rate_limiter.is_rate_limited(key2, 10, 120)
        
        # Both should work
        assert isinstance(is_limited1, bool)
        assert isinstance(is_limited2, bool)
        
        # Rate info should reflect the limits
        assert rate_info1['limit'] == 5
        assert rate_info1['window'] == 60
        assert rate_info2['limit'] == 10
        assert rate_info2['window'] == 120
    
    def test_rate_limiter_edge_cases(self, rate_limiter):
        """Test rate limiter edge cases."""
        # Test with very low limit
        is_limited, rate_info = rate_limiter.is_rate_limited('edge_test', 1, 60)
        assert rate_info['limit'] == 1
        
        # Test with very high limit
        is_limited, rate_info = rate_limiter.is_rate_limited('edge_test_2', 1000, 3600)
        assert rate_info['limit'] == 1000
        assert rate_info['window'] == 3600
    
    def test_rate_limiter_consistency(self, rate_limiter):
        """Test that rate limiter returns consistent data structure."""
        keys_to_test = ['key1', 'key2', 'key3']
        
        for key in keys_to_test:
            is_limited, rate_info = rate_limiter.is_rate_limited(key, 10, 60)
            
            # Check consistent structure
            assert isinstance(is_limited, bool)
            assert isinstance(rate_info, dict)
            
            # Check all required fields are present
            required_fields = ['requests', 'limit', 'remaining', 'window', 'reset_time']
            for field in required_fields:
                assert field in rate_info
            
            # Check non-None fields (reset_time can be None when Redis is unavailable)
            assert rate_info['requests'] is not None
            assert rate_info['limit'] is not None
            assert rate_info['remaining'] is not None
            assert rate_info['window'] is not None
            # reset_time can be None in fallback mode, so don't assert it's not None