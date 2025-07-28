"""
Rate limiting system for Garak Dashboard public API.

This module provides Redis-based rate limiting with different limits
per API key and endpoint type.
"""

import os
import redis
import time
import logging
from typing import Optional, Dict, Any
from flask import request, jsonify, current_app, g
from functools import wraps


class RateLimiter:
    """Redis-based rate limiter for API endpoints."""
    
    def __init__(self, redis_url: str = None):
        """Initialize rate limiter with Redis connection."""
        if redis_url is None:
            redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self.redis_client.ping()
            print(f"Connected to Redis for rate limiting: {redis_url}")
        except (redis.ConnectionError, redis.TimeoutError) as e:
            print(f"Redis connection failed: {e}. Rate limiting disabled.")
            self.redis_client = None
    
    def is_rate_limited(self, key: str, limit: int, window: int = 60) -> tuple[bool, Dict[str, Any]]:
        """
        Check if a key is rate limited using sliding window algorithm.
        
        Args:
            key: Unique identifier (e.g., API key + endpoint)
            limit: Maximum requests allowed in window
            window: Time window in seconds (default: 60)
            
        Returns:
            tuple: (is_limited, rate_info)
        """
        if not self.redis_client:
            # If Redis is not available, don't rate limit
            return False, {'requests': 0, 'limit': limit, 'window': window, 'reset_time': None, 'remaining': limit}
        
        current_time = time.time()
        window_start = current_time - window
        
        try:
            pipe = self.redis_client.pipeline()
            
            # Remove expired entries
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current requests in window
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(current_time): current_time})
            
            # Set expiration for the key
            pipe.expire(key, window * 2)
            
            results = pipe.execute()
            request_count = results[1]
            
            # Calculate reset time (when oldest request in window expires)
            oldest_request = self.redis_client.zrange(key, 0, 0, withscores=True)
            reset_time = None
            if oldest_request:
                reset_time = int(oldest_request[0][1] + window)
            
            rate_info = {
                'requests': request_count + 1,  # +1 for current request
                'limit': limit,
                'window': window,
                'reset_time': reset_time,
                'remaining': max(0, limit - (request_count + 1))
            }
            
            is_limited = request_count >= limit
            
            if is_limited:
                # Remove the current request since it's being denied
                self.redis_client.zrem(key, str(current_time))
                rate_info['requests'] = request_count
            
            return is_limited, rate_info
            
        except redis.RedisError as e:
            print(f"Redis error in rate limiting: {e}")
            # If Redis fails, don't rate limit
            return False, {'requests': 0, 'limit': limit, 'window': window, 'reset_time': None, 'remaining': limit}
    
    def get_rate_info(self, key: str, limit: int, window: int = 60) -> Dict[str, Any]:
        """Get current rate limiting info without incrementing counter."""
        if not self.redis_client:
            return {'requests': 0, 'limit': limit, 'window': window, 'reset_time': None, 'remaining': limit}
        
        current_time = time.time()
        window_start = current_time - window
        
        try:
            # Clean expired entries and count current requests
            pipe = self.redis_client.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            results = pipe.execute()
            
            request_count = results[1]
            
            # Calculate reset time
            oldest_request = self.redis_client.zrange(key, 0, 0, withscores=True)
            reset_time = None
            if oldest_request:
                reset_time = int(oldest_request[0][1] + window)
            
            return {
                'requests': request_count,
                'limit': limit,
                'window': window,
                'reset_time': reset_time,
                'remaining': max(0, limit - request_count)
            }
            
        except redis.RedisError as e:
            print(f"Redis error getting rate info: {e}")
            return {'requests': 0, 'limit': limit, 'window': window, 'reset_time': None, 'remaining': limit}


# Global rate limiter instance
rate_limiter = RateLimiter()


def rate_limit(limit: int = None, window: int = 60, per_key: bool = True, 
               endpoint_specific: bool = True):
    """
    Decorator to apply rate limiting to API endpoints.
    
    Args:
        limit: Requests per window (defaults to API key's rate_limit)
        window: Time window in seconds (default: 60)
        per_key: Apply limit per API key (True) or globally (False)
        endpoint_specific: Include endpoint in rate limit key (True) or apply across all endpoints (False)
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(*args, **kwargs):
            # Get API key info from g (set by api_key_required decorator)
            api_key_info = getattr(g, 'api_key_info', None)
            
            if not api_key_info:
                # If no API key info, use IP-based rate limiting
                client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
                rate_key = f"rate_limit:ip:{client_ip}"
                effective_limit = limit or 10  # Default for unauthenticated requests
            else:
                # Use API key for rate limiting
                key_id = api_key_info['id']
                effective_limit = limit or api_key_info.get('rate_limit', 100)
                
                if per_key:
                    if endpoint_specific:
                        # Rate limit per API key per endpoint
                        endpoint = f"{request.method}:{request.endpoint}"
                        rate_key = f"rate_limit:key:{key_id}:endpoint:{endpoint}"
                    else:
                        # Rate limit per API key across all endpoints
                        rate_key = f"rate_limit:key:{key_id}"
                else:
                    # Global rate limit (same for all keys)
                    rate_key = "rate_limit:global"
            
            # Check rate limit
            is_limited, rate_info = rate_limiter.is_rate_limited(rate_key, effective_limit, window)
            
            if is_limited:
                # Return rate limit exceeded error
                response = jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Too many requests. Limit: {effective_limit} per {window} seconds',
                    'rate_limit': rate_info
                })
                response.status_code = 429
                
                # Add rate limit headers
                response.headers['X-RateLimit-Limit'] = str(effective_limit)
                response.headers['X-RateLimit-Remaining'] = str(rate_info['remaining'])
                response.headers['X-RateLimit-Reset'] = str(rate_info['reset_time'] or '')
                response.headers['X-RateLimit-Window'] = str(window)
                
                return response
            
            # Add rate limit headers to successful responses
            def add_rate_limit_headers(response):
                response.headers['X-RateLimit-Limit'] = str(effective_limit)
                response.headers['X-RateLimit-Remaining'] = str(rate_info['remaining'])
                response.headers['X-RateLimit-Reset'] = str(rate_info['reset_time'] or '')
                response.headers['X-RateLimit-Window'] = str(window)
                return response
            
            # Execute the view function
            result = view_func(*args, **kwargs)
            
            # Add headers to response
            if hasattr(result, 'headers'):
                add_rate_limit_headers(result)
            
            return result
        
        return wrapped_view
    return decorator


def get_rate_limit_status(api_key_info: Dict[str, Any] = None) -> Dict[str, Any]:
    """Get current rate limit status for an API key."""
    if not api_key_info:
        return {'error': 'No API key information available'}
    
    key_id = api_key_info['id']
    limit = api_key_info.get('rate_limit', 100)
    
    # Get rate info for different scopes
    global_key = f"rate_limit:key:{key_id}"
    global_info = rate_limiter.get_rate_info(global_key, limit)
    
    # Get per-endpoint info for common endpoints
    endpoints_info = {}
    common_endpoints = [
        'GET:api_v1.list_scans',
        'POST:api_v1.create_scan', 
        'GET:api_v1.get_scan_status',
        'GET:api_v1.get_scan_progress'
    ]
    
    for endpoint in common_endpoints:
        endpoint_key = f"rate_limit:key:{key_id}:endpoint:{endpoint}"
        endpoint_info = rate_limiter.get_rate_info(endpoint_key, limit)
        endpoints_info[endpoint] = endpoint_info
    
    return {
        'api_key': api_key_info['key_prefix'],
        'global_rate_limit': global_info,
        'endpoint_rate_limits': endpoints_info
    }