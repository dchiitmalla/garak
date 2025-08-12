Rate Limiting
=============

API rate limits by endpoint.

Rate Limits by Endpoint
-----------------------

.. list-table::
   :header-rows: 1

   * - Endpoint
     - Method
     - Limit
   * - ``/api/v1/scans``
     - POST
     - 10/minute
   * - ``/api/v1/scans``
     - GET
     - 100/minute
   * - ``/api/v1/scans/{id}``
     - GET
     - 200/minute
   * - ``/api/v1/scans/{id}/status``
     - GET
     - 300/minute
   * - ``/api/v1/scans/{id}/progress``
     - GET
     - 500/minute
   * - ``/api/v1/scans/{id}/reports/{type}``
     - GET
     - 50/minute
   * - ``/api/v1/generators``
     - GET
     - 100/minute
   * - ``/api/v1/probes``
     - GET
     - 100/minute

Rate Limit Headers
------------------

Response headers in API responses:

* ``X-RateLimit-Limit`` - Maximum requests allowed
* ``X-RateLimit-Remaining`` - Requests remaining  
* ``X-RateLimit-Reset`` - When limit resets
* ``X-RateLimit-Window`` - Window duration

Check Rate Limit Status
-----------------------

.. http:get:: /api/v1/admin/api-keys/(int:key_id)/rate-limit

   Get current rate limit usage for an API key.

   **Rate limit:** 100 requests/minute

   .. code-block:: bash

      curl -H "X-API-Key: your_api_key_here" \
           https://your-api-domain.com/api/v1/admin/api-keys/{key_id}/rate-limit

   **Response:**

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

Usage Tips
----------

- Monitor ``X-RateLimit-Remaining`` header in responses
- Handle HTTP 429 responses by waiting before retry
- Space out requests to stay under limits

Rate Limit Exceeded
-------------------

HTTP 429 response when limits exceeded:

.. code-block:: json

   {
     "error": "rate_limit_exceeded",
     "message": "Too many requests. Rate limit exceeded."
   }