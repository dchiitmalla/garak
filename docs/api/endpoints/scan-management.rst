Scan Management
===============

Core endpoints for creating and managing security scans.

Create Scan
-----------

.. http:post:: /api/v1/scans

   Create a new security scan.

   **Rate limit:** 10 scans/minute

   **Headers:**
   
   * ``X-API-Key: your_api_key`` (required)
   * ``Content-Type: application/json``

   **Request Example:**

   .. code-block:: bash

      curl -X POST https://your-api-domain.com/api/v1/scans \
           -H "X-API-Key: your_api_key_here" \
           -H "Content-Type: application/json" \
           -d '{
             "generator": "openai",
             "model_name": "gpt-3.5-turbo",
             "probe_categories": ["hallucination"],
             "api_keys": {
               "openai_api_key": "sk-your_openai_key"
             },
             "name": "GPT-3.5 Security Test"
           }'

   **Required Fields:**

   * ``generator`` - Model provider (openai, huggingface, anthropic, etc.)
   * ``model_name`` - Specific model to test

   **Optional Fields:**

   * ``probe_categories`` - Categories like ["hallucination", "security"] (default: all)
   * ``probes`` - Specific probe names (overrides categories)
   * ``api_keys`` - Provider API keys (see :doc:`../api-keys-reference` for key names by generator)
   * ``name`` - Scan name
   * ``description`` - Scan description  
   * ``parallel_attempts`` - Parallel attempts 1-10 (default: 1)

   **Response:**

   .. code-block:: json

      {
        "scan_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "message": "Scan created successfully",
        "metadata": {
          "name": "GPT-3.5 Security Test", 
          "status": "pending",
          "created_at": "2024-01-15T10:30:00Z",
          "generator": "openai",
          "model_name": "gpt-3.5-turbo"
        }
      }

Monitor Scan
------------

.. http:get:: /api/v1/scans/(str:scan_id)/progress

   Get real-time scan progress with live output.

   **Rate limit:** 500 requests/minute

   .. code-block:: bash

      curl -H "X-API-Key: your_api_key_here" \
           https://your-api-domain.com/api/v1/scans/{scan_id}/progress

   **Response:**

   .. code-block:: json

      {
        "status": "running",
        "progress": 65,
        "completed": false,
        "elapsed_time": "3m 45s", 
        "time_remaining": "1m 50s",
        "output": "Running probe: misleading.FalseAssertion\nGenerating responses..."
      }

.. http:get:: /api/v1/scans/(str:scan_id)/status

   Get lightweight scan status (for polling).

   **Rate limit:** 300 requests/minute

   **Response:**

   .. code-block:: json

      {
        "scan_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890", 
        "status": "completed",
        "created_at": "2024-01-15T10:30:00Z",
        "completed_at": "2024-01-15T10:45:30Z"
      }

Get Results
-----------

.. http:get:: /api/v1/scans/(str:scan_id)

   Get complete scan details and results.

   **Rate limit:** 200 requests/minute

   .. code-block:: bash

      curl -H "X-API-Key: your_api_key_here" \
           https://your-api-domain.com/api/v1/scans/{scan_id}

Download Reports
----------------

.. http:get:: /api/v1/scans/(str:scan_id)/reports/json

   Download JSON report.

   **Rate limit:** 50 requests/minute

   .. code-block:: bash

      curl -H "X-API-Key: your_api_key_here" \
           https://your-api-domain.com/api/v1/scans/{scan_id}/reports/json \
           -o report.json

.. http:get:: /api/v1/scans/(str:scan_id)/reports/html

   Download HTML report.

   .. code-block:: bash

      curl -H "X-API-Key: your_api_key_here" \
           https://your-api-domain.com/api/v1/scans/{scan_id}/reports/html \
           -o report.html

List Scans  
----------

.. http:get:: /api/v1/scans

   List your scans with pagination.

   **Rate limit:** 100 requests/minute

   **Query Parameters:**

   * ``page`` - Page number (default: 1)
   * ``per_page`` - Items per page, max 100 (default: 20)
   * ``status`` - Filter by: pending, running, completed, failed

   .. code-block:: bash

      curl -H "X-API-Key: your_api_key_here" \
           "https://your-api-domain.com/api/v1/scans?status=completed&per_page=50"

Manage Scans
------------

.. http:patch:: /api/v1/scans/(str:scan_id)

   Update scan name/description.

   **Rate limit:** 50 requests/minute

   .. code-block:: bash

      curl -X PATCH -H "X-API-Key: your_api_key_here" \
           -H "Content-Type: application/json" \
           -d '{"name": "Updated scan name"}' \
           https://your-api-domain.com/api/v1/scans/{scan_id}

.. http:delete:: /api/v1/scans/(str:scan_id)

   Cancel a running scan.

   **Rate limit:** 20 requests/minute

   .. code-block:: bash

      curl -X DELETE -H "X-API-Key: your_api_key_here" \
           https://your-api-domain.com/api/v1/scans/{scan_id}

   .. note::
      Cancelled scans cannot be restarted.

Scan States
-----------

Scans progress through these states:

* **pending** → **running** → **completed**
* **failed** - Scan encountered errors  
* **cancelled** - Manually cancelled

Status Codes
------------

* **200** - Success
* **201** - Scan created
* **400** - Invalid parameters (check discovery endpoints)
* **401** - Missing/invalid API key
* **404** - Scan not found 
* **429** - Rate limit exceeded
* **500** - Internal error

Notes
-----

* **Test Mode:** Cloud providers fall back to GPT-2 test mode if API keys missing
* **Discovery:** Use ``/api/v1/generators`` and ``/api/v1/probes`` to find valid values
* **Authentication:** All endpoints require ``X-API-Key: your_api_key`` header