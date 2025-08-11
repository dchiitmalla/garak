Error Handling
==============

This guide covers comprehensive error handling for the Garak Scans API.

Error Response Format
---------------------

All API errors follow a consistent JSON format:

.. code-block:: json

   {
     "error": "error_code",
     "message": "Human-readable error description",
     "details": {
       "field": "Additional context about the error"
     },
     "timestamp": "2024-01-15T10:30:00Z"
   }

HTTP Status Codes
-----------------

The API uses standard HTTP status codes:

Success Codes
~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1

   * - Code
     - Description
     - When Used
   * - 200
     - OK
     - Successful GET, PATCH requests
   * - 201
     - Created
     - Successful POST requests (scan creation, API key creation)
   * - 204
     - No Content
     - Successful DELETE requests

Client Error Codes (4xx)
~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1

   * - Code
     - Error Type
     - Description
     - Common Causes
   * - 400
     - Bad Request
     - Invalid request data
     - Missing required fields, invalid JSON, unsupported values
   * - 401
     - Unauthorized
     - Authentication required
     - Missing API key, invalid API key format
   * - 403
     - Forbidden
     - Insufficient permissions
     - API key lacks required permissions, expired key
   * - 404
     - Not Found
     - Resource doesn't exist
     - Invalid scan ID, report not available
   * - 409
     - Conflict
     - Resource conflict
     - Scan already running, duplicate operation
   * - 422
     - Unprocessable Entity
     - Valid JSON but invalid data
     - Invalid generator/model combination, probe conflicts
   * - 429
     - Too Many Requests
     - Rate limit exceeded
     - Too many requests in time window

Server Error Codes (5xx)
~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1

   * - Code
     - Error Type  
     - Description
     - Action Required
   * - 500
     - Internal Server Error
     - Unexpected server error
     - Retry after delay, contact support if persists
   * - 502
     - Bad Gateway
     - Upstream service error
     - Check external service status (OpenAI, etc.)
   * - 503
     - Service Unavailable
     - Server overloaded
     - Retry with exponential backoff
   * - 504
     - Gateway Timeout
     - Request timeout
     - Increase timeout or reduce request complexity

Common Error Scenarios
----------------------

Authentication Errors
~~~~~~~~~~~~~~~~~~~~~

**Missing API Key (401)**

.. code-block:: json

   {
     "error": "api_key_required",
     "message": "API key is required for this endpoint",
     "timestamp": "2024-01-15T10:30:00Z"
   }

**Invalid API Key (401)**

.. code-block:: json

   {
     "error": "invalid_api_key", 
     "message": "The provided API key is invalid or has been revoked",
     "timestamp": "2024-01-15T10:30:00Z"
   }

**Expired API Key (403)**

.. code-block:: json

   {
     "error": "api_key_expired",
     "message": "API key has expired",
     "details": {
       "expires_at": "2024-01-10T00:00:00Z"
     },
     "timestamp": "2024-01-15T10:30:00Z"
   }

**Insufficient Permissions (403)**

.. code-block:: json

   {
     "error": "insufficient_permissions",
     "message": "API key does not have required permissions for this operation",
     "details": {
       "required": "write",
       "current": ["read"]
     },
     "timestamp": "2024-01-15T10:30:00Z"
   }

Validation Errors
~~~~~~~~~~~~~~~~~

**Missing Required Fields (400)**

.. code-block:: json

   {
     "error": "validation_error",
     "message": "Missing required fields",
     "details": {
       "missing_fields": ["generator", "model_name"]
     },
     "timestamp": "2024-01-15T10:30:00Z"
   }

**Invalid Generator (400)**

.. code-block:: json

   {
     "error": "invalid_generator",
     "message": "Unknown generator specified",
     "details": {
       "generator": "invalid_gen",
       "available": ["openai", "huggingface", "anthropic", "cohere", "ollama"]
     },
     "timestamp": "2024-01-15T10:30:00Z"
   }

**Invalid Model (400)**

.. code-block:: json

   {
     "error": "invalid_model",
     "message": "Model not supported by generator",
     "details": {
       "model": "invalid-model",
       "generator": "openai",
       "supported_models": ["gpt-4", "gpt-3.5-turbo"]
     },
     "timestamp": "2024-01-15T10:30:00Z"
   }

**Invalid Probe Category (400)**

.. code-block:: json

   {
     "error": "invalid_probe_category",
     "message": "Unknown probe category specified",
     "details": {
       "category": "invalid_category",
       "available": ["dan", "security", "privacy", "toxicity", "hallucination"]
     },
     "timestamp": "2024-01-15T10:30:00Z"
   }

Resource Errors
~~~~~~~~~~~~~~~

**Scan Not Found (404)**

.. code-block:: json

   {
     "error": "scan_not_found",
     "message": "Scan with specified ID not found",
     "details": {
       "scan_id": "non-existent-scan-id"
     },
     "timestamp": "2024-01-15T10:30:00Z"
   }

**Report Not Available (404)**

.. code-block:: json

   {
     "error": "report_not_found",
     "message": "Report not available for this scan",
     "details": {
       "scan_id": "scan-id",
       "status": "running",
       "message": "Reports are only available for completed scans"
     },
     "timestamp": "2024-01-15T10:30:00Z"
   }

Rate Limiting Errors
~~~~~~~~~~~~~~~~~~~~

**Rate Limit Exceeded (429)**

.. code-block:: json

   {
     "error": "rate_limit_exceeded",
     "message": "Too many requests. Rate limit exceeded.",
     "details": {
       "limit": 10,
       "window": "60 seconds",
       "reset_at": "2024-01-15T10:31:00Z"
     },
     "timestamp": "2024-01-15T10:30:00Z"
   }

**Headers included:**

.. code-block:: text

   X-RateLimit-Limit: 10
   X-RateLimit-Remaining: 0
   X-RateLimit-Reset: 1642248660
   X-RateLimit-Window: 60

System Errors
~~~~~~~~~~~~~

**Job Execution Failed (500)**

.. code-block:: json

   {
     "error": "job_execution_failed",
     "message": "Scan execution failed due to system error",
     "details": {
       "scan_id": "scan-id",
       "error_type": "timeout",
       "message": "Scan timed out after 30 minutes"
     },
     "timestamp": "2024-01-15T10:30:00Z"
   }

**Database Error (500)**

.. code-block:: json

   {
     "error": "database_error", 
     "message": "Internal database error occurred",
     "timestamp": "2024-01-15T10:30:00Z"
   }

Error Handling Best Practices
-----------------------------

Python Error Handling
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import requests
   import time
   import random
   from requests.exceptions import HTTPError, ConnectionError, Timeout

   class GarakAPIError(Exception):
       """Base exception for Garak API errors"""
       pass

   class AuthenticationError(GarakAPIError):
       """Raised for authentication-related errors"""
       pass

   class RateLimitError(GarakAPIError):
       """Raised when rate limit is exceeded"""
       pass

   class ValidationError(GarakAPIError):
       """Raised for validation errors"""
       pass

   class ResourceNotFoundError(GarakAPIError):
       """Raised when requested resource is not found"""
       pass

   def handle_api_response(response):
       """Handle API response and raise appropriate exceptions"""
       if response.status_code == 200 or response.status_code == 201:
           return response.json()
       
       try:
           error_data = response.json()
       except ValueError:
           # Non-JSON error response
           error_data = {"error": "unknown", "message": response.text}
       
       error_code = error_data.get("error", "unknown")
       message = error_data.get("message", "Unknown error")
       
       if response.status_code == 401:
           raise AuthenticationError(f"Authentication failed: {message}")
       elif response.status_code == 403:
           if "expired" in message.lower():
               raise AuthenticationError(f"API key expired: {message}")
           else:
               raise AuthenticationError(f"Insufficient permissions: {message}")
       elif response.status_code == 404:
           raise ResourceNotFoundError(f"Resource not found: {message}")
       elif response.status_code == 400 or response.status_code == 422:
           raise ValidationError(f"Validation error: {message}")
       elif response.status_code == 429:
           raise RateLimitError(f"Rate limit exceeded: {message}")
       else:
           raise GarakAPIError(f"API error ({response.status_code}): {message}")

   def api_request_with_retry(func, *args, max_retries=3, backoff_factor=1, **kwargs):
       """Make API request with exponential backoff retry logic"""
       for attempt in range(max_retries + 1):
           try:
               response = func(*args, **kwargs)
               return handle_api_response(response)
           
           except RateLimitError as e:
               if attempt == max_retries:
                   raise e
               
               # Extract retry delay from error or use backoff
               wait_time = backoff_factor * (2 ** attempt) + random.uniform(0, 1)
               print(f"Rate limited. Waiting {wait_time:.2f} seconds before retry {attempt + 1}/{max_retries}")
               time.sleep(wait_time)
           
           except (ConnectionError, Timeout) as e:
               if attempt == max_retries:
                   raise GarakAPIError(f"Connection error after {max_retries} retries: {e}")
               
               wait_time = backoff_factor * (2 ** attempt)
               print(f"Connection error. Retrying in {wait_time} seconds...")
               time.sleep(wait_time)
           
           except (AuthenticationError, ValidationError, ResourceNotFoundError):
               # Don't retry these errors
               raise
           
           except GarakAPIError as e:
               if attempt == max_retries:
                   raise e
               
               # Retry server errors (5xx)
               wait_time = backoff_factor * (2 ** attempt)
               print(f"Server error. Retrying in {wait_time} seconds...")
               time.sleep(wait_time)

   # Usage example
   def create_scan_safely(config):
       try:
           return api_request_with_retry(
               requests.post,
               "http://localhost:8080/api/v1/scans",
               json=config,
               headers={"X-API-Key": "your_key", "Content-Type": "application/json"},
               max_retries=3
           )
       except AuthenticationError as e:
           print(f"Authentication error: {e}")
           return None
       except ValidationError as e:
           print(f"Invalid scan configuration: {e}")
           return None
       except RateLimitError as e:
           print(f"Rate limit exceeded: {e}")
           return None
       except GarakAPIError as e:
           print(f"API error: {e}")
           return None

Bash/cURL Error Handling
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   #!/bin/bash

   API_KEY="your_api_key_here"
   BASE_URL="http://localhost:8080/api/v1"

   # Function to handle API errors
   handle_api_error() {
       local response="$1"
       local http_code="$2"
       
       case $http_code in
           200|201)
               echo "$response"
               return 0
               ;;
           400)
               echo "❌ Bad Request: $(echo "$response" | jq -r '.message // "Invalid request"')"
               return 1
               ;;
           401)
               echo "❌ Authentication Error: Check your API key"
               return 1
               ;;
           403)
               echo "❌ Permission Error: API key lacks required permissions"
               return 1
               ;;
           404)
               echo "❌ Not Found: $(echo "$response" | jq -r '.message // "Resource not found"')"
               return 1
               ;;
           429)
               echo "⚠️ Rate Limited: Too many requests"
               return 2  # Special code for rate limiting
               ;;
           5*)
               echo "❌ Server Error: $(echo "$response" | jq -r '.message // "Internal server error"')"
               return 3  # Server error
               ;;
           *)
               echo "❌ Unknown Error (HTTP $http_code): $response"
               return 4
               ;;
       esac
   }

   # Function to make API request with retry
   api_request() {
       local method="$1"
       local endpoint="$2"
       local data="$3"
       local max_retries=3
       local retry_delay=1
       
       for attempt in $(seq 1 $max_retries); do
           echo "🔄 Attempt $attempt/$max_retries..."
           
           if [ "$method" = "POST" ]; then
               response=$(curl -s -w "\n%{http_code}" \
                   -X POST \
                   -H "X-API-Key: $API_KEY" \
                   -H "Content-Type: application/json" \
                   -d "$data" \
                   "$BASE_URL$endpoint")
           else
               response=$(curl -s -w "\n%{http_code}" \
                   -H "X-API-Key: $API_KEY" \
                   "$BASE_URL$endpoint")
           fi
           
           # Extract body and status code
           body=$(echo "$response" | head -n -1)
           http_code=$(echo "$response" | tail -n 1)
           
           handle_api_error "$body" "$http_code"
           result=$?
           
           case $result in
               0)
                   # Success
                   return 0
                   ;;
               1|4)
                   # Client error - don't retry
                   return $result
                   ;;
               2)
                   # Rate limited - wait longer
                   echo "⏳ Waiting ${retry_delay}s before retry..."
                   sleep $retry_delay
                   retry_delay=$((retry_delay * 2))
                   ;;
               3)
                   # Server error - retry with backoff
                   echo "⏳ Server error, waiting ${retry_delay}s before retry..."
                   sleep $retry_delay
                   retry_delay=$((retry_delay * 2))
                   ;;
           esac
           
           if [ $attempt -eq $max_retries ]; then
               echo "❌ Max retries exceeded"
               return $result
           fi
       done
   }

   # Usage examples
   echo "Creating scan..."
   scan_data='{"generator": "huggingface", "model_name": "gpt2", "probe_categories": ["toxicity"]}'
   result=$(api_request "POST" "/scans" "$scan_data")

   if [ $? -eq 0 ]; then
       echo "✅ Scan created successfully"
       scan_id=$(echo "$result" | jq -r '.scan_id')
       echo "📋 Scan ID: $scan_id"
   else
       echo "❌ Failed to create scan"
       exit 1
   fi

JavaScript/Node.js Error Handling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: javascript

   const axios = require('axios');

   class GarakAPIError extends Error {
       constructor(message, code, details) {
           super(message);
           this.name = 'GarakAPIError';
           this.code = code;
           this.details = details;
       }
   }

   class GarakAPI {
       constructor(apiKey, baseURL = 'http://localhost:8080/api/v1') {
           this.apiKey = apiKey;
           this.baseURL = baseURL;
           this.client = axios.create({
               baseURL,
               headers: {
                   'X-API-Key': apiKey,
                   'Content-Type': 'application/json'
               },
               timeout: 30000
           });
           
           // Add response interceptor for error handling
           this.client.interceptors.response.use(
               response => response,
               error => this.handleError(error)
           );
       }
       
       handleError(error) {
           if (error.response) {
               const { status, data } = error.response;
               const errorCode = data.error || 'unknown';
               const message = data.message || 'Unknown error';
               
               switch (status) {
                   case 400:
                       throw new GarakAPIError(`Validation Error: ${message}`, errorCode, data.details);
                   case 401:
                       throw new GarakAPIError(`Authentication Error: ${message}`, errorCode, data.details);
                   case 403:
                       throw new GarakAPIError(`Permission Error: ${message}`, errorCode, data.details);
                   case 404:
                       throw new GarakAPIError(`Not Found: ${message}`, errorCode, data.details);
                   case 429:
                       throw new GarakAPIError(`Rate Limited: ${message}`, errorCode, data.details);
                   default:
                       throw new GarakAPIError(`API Error (${status}): ${message}`, errorCode, data.details);
               }
           } else if (error.request) {
               throw new GarakAPIError('Network Error: No response received', 'network_error');
           } else {
               throw new GarakAPIError(`Request Error: ${error.message}`, 'request_error');
           }
       }
       
       async createScanWithRetry(config, maxRetries = 3) {
           for (let attempt = 1; attempt <= maxRetries; attempt++) {
               try {
                   const response = await this.client.post('/scans', config);
                   return response.data;
               } catch (error) {
                   if (error.code === 'rate_limit_exceeded' && attempt < maxRetries) {
                       const delay = Math.pow(2, attempt) * 1000; // Exponential backoff
                       console.log(`Rate limited. Waiting ${delay}ms before retry ${attempt + 1}/${maxRetries}`);
                       await new Promise(resolve => setTimeout(resolve, delay));
                       continue;
                   }
                   
                   if (error.code === 'network_error' && attempt < maxRetries) {
                       const delay = Math.pow(2, attempt) * 1000;
                       console.log(`Network error. Waiting ${delay}ms before retry ${attempt + 1}/${maxRetries}`);
                       await new Promise(resolve => setTimeout(resolve, delay));
                       continue;
                   }
                   
                   throw error;
               }
           }
       }
   }

   // Usage example
   async function main() {
       const api = new GarakAPI('your_api_key_here');
       
       try {
           const result = await api.createScanWithRetry({
               generator: 'huggingface',
               model_name: 'gpt2',
               probe_categories: ['toxicity']
           });
           
           console.log('✅ Scan created:', result.scan_id);
       } catch (error) {
           if (error instanceof GarakAPIError) {
               console.error(`❌ API Error: ${error.message}`);
               if (error.details) {
                   console.error('Details:', error.details);
               }
           } else {
               console.error(`❌ Unexpected Error: ${error.message}`);
           }
           process.exit(1);
       }
   }

Monitoring and Alerting
-----------------------

Health Check Integration
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import requests
   import time

   def check_api_health():
       """Check API health and return status"""
       try:
           response = requests.get("http://localhost:8080/api/v1/health", timeout=10)
           if response.status_code == 200:
               data = response.json()
               if data["status"] == "healthy":
                   return True, "API is healthy"
               else:
                   return False, f"API unhealthy: {data}"
           else:
               return False, f"API health check failed: HTTP {response.status_code}"
       except Exception as e:
           return False, f"API health check error: {e}"

   def monitor_api_health(check_interval=60):
       """Continuously monitor API health"""
       while True:
           healthy, message = check_api_health()
           timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
           
           if healthy:
               print(f"[{timestamp}] ✅ {message}")
           else:
               print(f"[{timestamp}] ❌ {message}")
               # Send alert here (email, Slack, etc.)
           
           time.sleep(check_interval)

Error Recovery Strategies
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   class GarakAPIClient:
       def __init__(self, api_key):
           self.api_key = api_key
           self.session = requests.Session()
           self.session.headers.update({
               'X-API-Key': api_key,
               'Content-Type': 'application/json'
           })
       
       def create_scan_with_fallback(self, primary_config, fallback_configs=None):
           """Create scan with fallback configurations"""
           configs_to_try = [primary_config]
           if fallback_configs:
               configs_to_try.extend(fallback_configs)
           
           last_error = None
           for i, config in enumerate(configs_to_try):
               try:
                   print(f"Trying configuration {i + 1}/{len(configs_to_try)}...")
                   response = self.session.post(
                       "http://localhost:8080/api/v1/scans",
                       json=config
                   )
                   handle_api_response(response)
                   return response.json()
               
               except ValidationError as e:
                   print(f"Configuration {i + 1} invalid: {e}")
                   last_error = e
                   continue
               except GarakAPIError as e:
                   print(f"Configuration {i + 1} failed: {e}")
                   last_error = e
                   if i == len(configs_to_try) - 1:  # Last config
                       raise e
           
           raise last_error or GarakAPIError("All configurations failed")

   # Usage
   api = GarakAPIClient("your_api_key")
   
   primary_config = {
       "generator": "openai",
       "model_name": "gpt-4",
       "probe_categories": ["dan", "security"],
       "api_keys": {"openai_api_key": "sk-..."}
   }
   
   fallback_configs = [
       {
           "generator": "openai",
           "model_name": "gpt-3.5-turbo",  # Fallback to cheaper model
           "probe_categories": ["dan"],     # Reduced scope
           "api_keys": {"openai_api_key": "sk-..."}
       },
       {
           "generator": "huggingface",      # Fallback to free model
           "model_name": "gpt2",
           "probe_categories": ["toxicity"]  # Basic testing only
       }
   ]
   
   try:
       result = api.create_scan_with_fallback(primary_config, fallback_configs)
       print("Scan created successfully:", result["scan_id"])
   except GarakAPIError as e:
       print("All scan configurations failed:", e)

Troubleshooting Guide
--------------------

Common Issues and Solutions
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Issue: Authentication keeps failing**

*Solutions:*
- Verify API key format (should start with "garak_")
- Check API key hasn't expired
- Ensure API key has correct permissions
- Try creating a new API key

**Issue: Scans fail immediately**

*Solutions:*
- Check generator and model_name are valid
- Verify external API keys (OpenAI, etc.) are provided and valid
- Ensure probe categories exist
- Check system health endpoint

**Issue: High failure rates in scans**

*Solutions:*
- Review probe selection (some are more aggressive)
- Check model compatibility with probes
- Consider reducing parallel_attempts
- Analyze specific failure patterns in reports

**Issue: Slow scan performance**

*Solutions:*
- Reduce number of probes or parallel attempts  
- Use faster models for initial testing
- Check system resources and concurrent scans
- Consider using probe-specific filtering

Debug Mode
~~~~~~~~~~

Enable debug logging for troubleshooting:

.. code-block:: python

   import logging
   import requests

   # Enable debug logging
   logging.basicConfig(level=logging.DEBUG)
   requests.packages.urllib3.disable_warnings()

   # Add request/response logging
   import http.client as http_client
   http_client.HTTPConnection.debuglevel = 1