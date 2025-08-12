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

Checking Your Rate Limit
-----------------------

You can check your current rate limit status by inspecting the response headers of any API request. The headers ``X-RateLimit-Limit``, ``X-RateLimit-Remaining``, and ``X-RateLimit-Reset`` are included in all responses.

Example (using curl):

.. code-block:: bash

   curl -i -H "X-API-Key: your_api_key" https://your-api-domain.com/api/v1/scans

Look for these headers in the response:

.. code-block:: text

   X-RateLimit-Limit: 100
   X-RateLimit-Remaining: 99
   X-RateLimit-Reset: 1723488000
   X-RateLimit-Window: 60

Best Practices for Rate Limits
-----------------------------

- Space out requests to avoid hitting the limit.
- Monitor ``X-RateLimit-Remaining`` to know when you are close to the limit.
- Handle HTTP 429 responses by backing off and retrying after the reset time.

Rate Limit Exceeded
-------------------

HTTP 429 response when limits exceeded:

.. code-block:: json

   {
     "error": "rate_limit_exceeded",
     "message": "Too many requests. Rate limit exceeded."
   }