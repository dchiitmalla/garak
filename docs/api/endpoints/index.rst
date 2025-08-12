API Endpoints Overview
=====================

RESTful endpoints for the Garak security scanning API.

.. toctree::
   :maxdepth: 1

   scan-management
   discovery  
   reports

Quick Reference
---------------

**Base URL:** ``https://your-api-domain.com/api/v1``

**Authentication:** ``X-API-Key: your_api_key`` (required for all endpoints)

**Content-Type:** ``application/json``

Core Endpoints
--------------

**Scan Management**

* ``POST /api/v1/scans`` - Create new security scan
* ``GET /api/v1/scans/{id}/progress`` - Monitor scan progress  
* ``GET /api/v1/scans/{id}/status`` - Get scan status
* ``GET /api/v1/scans`` - List your scans
* ``DELETE /api/v1/scans/{id}`` - Cancel scan

**Discovery**

* ``GET /api/v1/generators`` - List model providers
* ``GET /api/v1/probes`` - List security probe categories

**Reports**

* ``GET /api/v1/scans/{id}/reports/json`` - Download JSON report
* ``GET /api/v1/scans/{id}/reports/html`` - Download HTML report

**System**

* ``GET /api/v1/health`` - API health check (no auth required)
* ``GET /api/v1/info`` - API information (no auth required)

Rate Limits  
-----------

* **Scan creation:** 10/minute
* **Progress monitoring:** 500/minute  
* **Discovery:** 100/minute
* **Reports:** 50/minute

Rate limit headers included in responses:

* ``X-RateLimit-Limit`` - Maximum requests allowed per window
* ``X-RateLimit-Remaining`` - Requests remaining in current window  
* ``X-RateLimit-Reset`` - Unix timestamp when limit resets
* ``X-RateLimit-Window`` - Window duration in seconds

HTTP Status Codes
-----------------

* **200** - Success
* **201** - Scan created
* **400** - Invalid request (check parameters)
* **401** - Missing/invalid API key  
* **404** - Resource not found
* **429** - Rate limit exceeded
* **500** - Internal error

Error Format
------------

All errors return consistent JSON:

.. code-block:: json

   {
     "error": "invalid_parameters",
     "message": "Generator 'invalid' not found. Use /api/v1/generators to see available options."
   }

Getting Started
---------------

1. **Get API Key:** Use ``/api/v1/admin/bootstrap`` (first time) or get one from your admin
2. **Discover Options:** Check ``/api/v1/generators`` and ``/api/v1/probes``  
3. **Create Scan:** Post to ``/api/v1/scans`` with your parameters
4. **Monitor Progress:** Poll ``/api/v1/scans/{id}/progress`` for updates
5. **Download Results:** Get reports from ``/api/v1/scans/{id}/reports/{type}``