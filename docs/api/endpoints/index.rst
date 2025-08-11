API Endpoints Overview
=====================

The Garak Scans API provides RESTful endpoints organized into functional groups.

.. toctree::
   :maxdepth: 1

   scan-management
   discovery  
   reports
   admin
   system

Endpoint Categories
-------------------

Scan Management
~~~~~~~~~~~~~~~

Core endpoints for creating, monitoring, and managing security scans:

* ``POST /api/v1/scans`` - Create new scan
* ``GET /api/v1/scans`` - List all scans  
* ``GET /api/v1/scans/{id}`` - Get scan details
* ``GET /api/v1/scans/{id}/status`` - Get scan status
* ``PATCH /api/v1/scans/{id}`` - Update scan metadata
* ``DELETE /api/v1/scans/{id}`` - Cancel scan

Discovery
~~~~~~~~~

Endpoints for discovering available capabilities:

* ``GET /api/v1/generators`` - List model generators
* ``GET /api/v1/generators/{name}`` - Get generator details
* ``GET /api/v1/probes`` - List security probes
* ``GET /api/v1/probes/{category}`` - Get category probes

Report Management
~~~~~~~~~~~~~~~~~

Endpoints for accessing scan results:

* ``GET /api/v1/scans/{id}/reports`` - List available reports
* ``GET /api/v1/scans/{id}/reports/{type}`` - Download report

Administrative
~~~~~~~~~~~~~~

Admin-only endpoints for system management:

* ``POST /api/v1/admin/bootstrap`` - Create first admin key
* ``GET /api/v1/admin/api-keys`` - Manage API keys
* ``GET /api/v1/admin/stats`` - System statistics

System Information
~~~~~~~~~~~~~~~~~~

Public endpoints for system status:

* ``GET /api/v1/info`` - API capabilities
* ``GET /api/v1/health`` - System health check

Rate Limits
-----------

All endpoints are subject to rate limiting:

.. list-table::
   :header-rows: 1

   * - Endpoint Category
     - Default Limit
     - Window
   * - Scan Creation
     - 10 requests
     - Per minute
   * - Read Operations
     - 100-300 requests
     - Per minute
   * - Write Operations  
     - 20-50 requests
     - Per minute
   * - Admin Operations
     - Varies
     - Per minute

Rate limit information is included in response headers:

* ``X-RateLimit-Limit`` - Maximum requests allowed
* ``X-RateLimit-Remaining`` - Requests remaining
* ``X-RateLimit-Reset`` - Reset timestamp

Base URL
--------

All endpoints use the base URL:

.. code-block:: text

   http://localhost:8080/api/v1

Authentication
--------------

All endpoints except ``/health`` and ``/info`` require authentication.
See :doc:`../authentication` for details.

Content Types
-------------

* **Request Content-Type**: ``application/json``
* **Response Content-Type**: ``application/json``
* **Report Downloads**: Various (``application/json``, ``text/html``, etc.)

HTTP Methods
------------

* **GET** - Retrieve data (idempotent)
* **POST** - Create resources  
* **PATCH** - Update resources (partial)
* **DELETE** - Remove/cancel resources

Error Responses
---------------

All errors follow a consistent format:

.. code-block:: json

   {
     "error": "error_code",
     "message": "Human-readable description", 
     "details": {},
     "timestamp": "2024-01-15T10:30:00Z"
   }

Common HTTP status codes:

* **200** - Success
* **201** - Created
* **400** - Bad Request
* **401** - Unauthorized
* **403** - Forbidden
* **404** - Not Found
* **429** - Rate Limited
* **500** - Server Error