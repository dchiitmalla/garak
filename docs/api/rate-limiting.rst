Rate Limiting
=============

The Garak Scans API implements rate limiting to ensure fair usage and system stability.

Overview
--------

Rate limiting controls how frequently you can make API requests. Each API key has individual limits based on its permission level and configuration.

Rate Limits by Endpoint
-----------------------

Default Limits by Category
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1

   * - Category
     - Default Limit
     - Window
     - Applies To
   * - Scan Creation
     - 10 requests
     - Per minute
     - ``POST /api/v1/scans``
   * - Read Operations
     - 100-300 requests  
     - Per minute
     - ``GET`` endpoints (status, details, lists)
   * - Write Operations
     - 20-50 requests
     - Per minute
     - ``PATCH``, ``DELETE`` endpoints
   * - Admin Operations
     - 10-100 requests
     - Per minute
     - ``/api/v1/admin/*`` endpoints
   * - Discovery
     - 100 requests
     - Per minute
     - ``/api/v1/generators``, ``/api/v1/probes``
   * - System Info
     - 1000 requests
     - Per minute
     - ``/api/v1/health``, ``/api/v1/info``

Specific Endpoint Limits
~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1

   * - Endpoint
     - Method
     - Default Limit
     - Permission Required
   * - ``/api/v1/scans``
     - POST
     - 10/minute
     - write
   * - ``/api/v1/scans``
     - GET
     - 100/minute
     - read
   * - ``/api/v1/scans/{id}``
     - GET
     - 200/minute
     - read
   * - ``/api/v1/scans/{id}/status``
     - GET
     - 300/minute
     - read
   * - ``/api/v1/scans/{id}/progress``
     - GET
     - 500/minute
     - read
   * - ``/api/v1/scans/{id}/reports/{type}``
     - GET
     - 50/minute
     - read
   * - ``/api/v1/generators``
     - GET
     - 100/minute
     - read
   * - ``/api/v1/probes``
     - GET
     - 100/minute
     - read
   * - ``/api/v1/admin/api-keys``
     - POST
     - 10/minute
     - admin
   * - ``/api/v1/health``
     - GET
     - 1000/minute
     - none
   * - ``/api/v1/info``
     - GET
     - 1000/minute
     - none

Rate Limit Headers
------------------

Every API response includes rate limiting information in HTTP headers:

Response Headers
~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1

   * - Header
     - Description
     - Example
   * - ``X-RateLimit-Limit``
     - Maximum requests allowed in window
     - ``100``
   * - ``X-RateLimit-Remaining``
     - Requests remaining in current window
     - ``87``
   * - ``X-RateLimit-Reset``
     - Unix timestamp when window resets
     - ``1642248660``
   * - ``X-RateLimit-Window``
     - Window duration in seconds
     - ``60``

Example Response
~~~~~~~~~~~~~~~

.. code-block:: http

   HTTP/1.1 200 OK
   X-RateLimit-Limit: 100
   X-RateLimit-Remaining: 87
   X-RateLimit-Reset: 1642248660
   X-RateLimit-Window: 60
   Content-Type: application/json

   {
     "scans": [...],
     "total": 25
   }

Rate Limit Exceeded Response
---------------------------

When rate limits are exceeded, the API returns a ``429 Too Many Requests`` status:

.. code-block:: http

   HTTP/1.1 429 Too Many Requests
   X-RateLimit-Limit: 10
   X-RateLimit-Remaining: 0
   X-RateLimit-Reset: 1642248720
   Content-Type: application/json

   {
     "error": "rate_limit_exceeded",
     "message": "Too many requests. Rate limit exceeded.",
     "details": {
       "limit": 10,
       "window": "60 seconds",
       "reset_at": "2024-01-15T10:32:00Z",
       "retry_after": 45
     },
     "timestamp": "2024-01-15T10:31:15Z"
   }

Custom Rate Limits
------------------

API Key Configuration
~~~~~~~~~~~~~~~~~~~~

Rate limits can be customized per API key during creation:

.. code-block:: bash

   curl -X POST http://localhost:8080/api/v1/admin/api-keys \
        -H "X-API-Key: admin_key" \
        -H "Content-Type: application/json" \
        -d '{
          "name": "High Volume Scanner",
          "description": "For automated scanning workloads",
          "permissions": ["read", "write"],
          "rate_limit": 500,
          "expires_days": 30
        }'

Rate Limit Tiers
~~~~~~~~~~~~~~~~

Common configurations by use case:

.. list-table::
   :header-rows: 1

   * - Use Case
     - Rate Limit
     - Suitable For
   * - Development/Testing
     - 10-50/minute
     - Individual developers, small tests
   * - Production API
     - 100-300/minute
     - Production applications, moderate load
   * - High Volume
     - 500-1000/minute
     - Large-scale scanning, batch processing
   * - Enterprise
     - 1000+/minute
     - Enterprise deployments, critical workloads

Monitoring Rate Limits
---------------------

Check Rate Limit Status
~~~~~~~~~~~~~~~~~~~~~~

For admin users, check current rate limit status:

.. code-block:: bash

   curl -H "X-API-Key: admin_key" \
        "http://localhost:8080/api/v1/admin/api-keys/123/rate-limit"

Response:

.. code-block:: json

   {
     "api_key_id": 123,
     "current_usage": {
       "requests_in_window": 45,
       "limit": 100,
       "remaining": 55,
       "reset_time": "2024-01-15T10:32:00Z"
     }
   }

Best Practices
--------------

Handling Rate Limits
~~~~~~~~~~~~~~~~~~~~

**1. Exponential Backoff**

When you receive a 429 response, wait before retrying:

.. code-block:: python

   import time
   import random
   import requests

   def api_request_with_backoff(url, max_retries=5):
       for attempt in range(max_retries):
           response = requests.get(url, headers={"X-API-Key": "your_key"})
           
           if response.status_code == 429:
               # Rate limited - wait before retry
               wait_time = (2 ** attempt) + random.uniform(0, 1)
               print(f"Rate limited. Waiting {wait_time:.2f} seconds...")
               time.sleep(wait_time)
               continue
           
           return response
       
       raise Exception("Max retries exceeded")

**2. Monitor Rate Limit Headers**

Check headers to avoid hitting limits:

.. code-block:: python

   def check_rate_limit_status(response):
       limit = int(response.headers.get('X-RateLimit-Limit', 0))
       remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
       
       if remaining < limit * 0.1:  # Less than 10% remaining
           print(f"Warning: Only {remaining}/{limit} requests remaining")
           return True  # Should slow down
       
       return False

**3. Request Spacing**

Space out requests to stay under limits:

.. code-block:: python

   import time

   class RateLimitedClient:
       def __init__(self, api_key, requests_per_minute=60):
           self.api_key = api_key
           self.min_interval = 60.0 / requests_per_minute
           self.last_request_time = 0
       
       def make_request(self, url, **kwargs):
           # Ensure minimum interval between requests
           elapsed = time.time() - self.last_request_time
           if elapsed < self.min_interval:
               time.sleep(self.min_interval - elapsed)
           
           response = requests.get(url, 
                                 headers={"X-API-Key": self.api_key},
                                 **kwargs)
           self.last_request_time = time.time()
           return response

**4. Batch Operations**

Group related operations to minimize requests:

.. code-block:: python

   # Instead of multiple individual requests
   # for scan_id in scan_ids:
   #     get_scan_status(scan_id)

   # Use list endpoint to get multiple results
   def get_multiple_scan_status(scan_ids):
       response = requests.get(
           "http://localhost:8080/api/v1/scans",
           params={"per_page": 100},
           headers={"X-API-Key": "your_key"}
       )
       
       all_scans = response.json()["scans"]
       return {scan["scan_id"]: scan for scan in all_scans 
               if scan["scan_id"] in scan_ids}

**5. Caching**

Cache responses for endpoints that don't change frequently:

.. code-block:: python

   import time

   class CachedAPIClient:
       def __init__(self, api_key):
           self.api_key = api_key
           self.cache = {}
           self.cache_duration = 300  # 5 minutes
       
       def get_generators(self):
           cache_key = "generators"
           now = time.time()
           
           # Check cache first
           if (cache_key in self.cache and 
               now - self.cache[cache_key]['timestamp'] < self.cache_duration):
               return self.cache[cache_key]['data']
           
           # Make API request
           response = requests.get("http://localhost:8080/api/v1/generators",
                                 headers={"X-API-Key": self.api_key})
           data = response.json()
           
           # Cache the result
           self.cache[cache_key] = {'data': data, 'timestamp': now}
           return data

Error Handling Example
~~~~~~~~~~~~~~~~~~~~~

Complete error handling with rate limiting:

.. code-block:: python

   def safe_api_request(url, max_retries=3):
       for attempt in range(max_retries):
           try:
               response = requests.get(url, headers={"X-API-Key": "your_key"})
               
               if response.status_code == 200:
                   return response.json()
               elif response.status_code == 429:
                   # Rate limited
                   retry_after = int(response.headers.get('Retry-After', 60))
                   print(f"Rate limited. Waiting {retry_after} seconds...")
                   time.sleep(retry_after)
                   continue
               else:
                   print(f"API error: {response.status_code}")
                   return None
           
           except requests.RequestException as e:
               print(f"Request error: {e}")
               time.sleep(2 ** attempt)  # Exponential backoff
       
       print("Max retries exceeded")
       return None

CI/CD Integration
~~~~~~~~~~~~~~~~

For automated testing and deployment pipelines:

.. code-block:: python

   def ci_friendly_scan_creation(scan_config, timeout=600):
       """Create scan with CI/CD friendly rate limiting"""
       
       # Conservative rate limiting for CI
       client = RateLimitedClient("your_api_key", requests_per_minute=20)
       
       try:
           # Create scan
           response = client.make_request(
               "http://localhost:8080/api/v1/scans",
               method="POST",
               json=scan_config
           )
           
           if response.status_code != 201:
               return None
           
           scan_id = response.json()["scan_id"]
           
           # Wait for completion with appropriate polling interval
           start_time = time.time()
           while time.time() - start_time < timeout:
               status_response = client.make_request(
                   f"http://localhost:8080/api/v1/scans/{scan_id}/status"
               )
               
               if status_response.status_code == 200:
                   status = status_response.json()["status"]
                   if status in ["completed", "failed", "cancelled"]:
                       return scan_id
               
               time.sleep(30)  # Poll every 30 seconds
           
           return None  # Timeout
           
       except Exception as e:
           print(f"CI scan creation failed: {e}")
           return None

Common Issues and Solutions
--------------------------

Frequently Asked Questions
~~~~~~~~~~~~~~~~~~~~~~~~~

**Q: Why am I getting rate limited when I'm not making many requests?**

A: Rate limits apply per API key across all your applications. Check if you have multiple services using the same key.

**Q: Can I get a higher rate limit?**

A: Yes, rate limits can be configured when creating API keys. Contact your admin or create a new key with higher limits.

**Q: Do rate limits reset at fixed intervals?**

A: Rate limits use a sliding window approach, so they reset continuously rather than at fixed intervals.

**Q: What happens if I hit the rate limit?**

A: You'll receive a 429 status code. Wait for the time indicated in the response headers before retrying.

**Q: Are rate limits shared between different endpoints?**

A: Rate limits are applied both globally per API key and specifically per endpoint. Each has its own limits.

Troubleshooting
~~~~~~~~~~~~~~

**Issue: Unexpected rate limiting**

Solutions:
- Check if multiple applications are using the same API key
- Monitor rate limit headers in responses
- Implement request logging to track usage patterns
- Consider using separate API keys for different services

**Issue: Scans failing due to rate limits**

Solutions:
- Reduce parallel_attempts in scan configurations
- Space out scan creation requests
- Use higher-limit API keys for batch operations
- Implement retry logic with appropriate backoff

**Issue: Development testing hitting limits**

Solutions:
- Use separate API keys for development vs production
- Implement caching for repeated discovery requests
- Use mock responses for unit testing
- Configure lower rate limits for development environments

Monitoring and Alerting
~~~~~~~~~~~~~~~~~~~~~~

Set up monitoring to track rate limit usage:

.. code-block:: python

   def monitor_api_usage(api_key):
       """Monitor API usage and alert on high usage"""
       headers = {"X-API-Key": api_key}
       
       response = requests.get("http://localhost:8080/api/v1/health", headers=headers)
       
       limit = int(response.headers.get('X-RateLimit-Limit', 0))
       remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
       
       if limit > 0:
           usage_percent = ((limit - remaining) / limit) * 100
           print(f"API Usage: {usage_percent:.1f}% ({limit - remaining}/{limit})")
           
           if usage_percent > 80:
               print("⚠️ High API usage warning!")
               # Send alert notification
           
           return usage_percent
       
       return 0

For production deployments, integrate this monitoring with your alerting system to proactively manage rate limit usage.