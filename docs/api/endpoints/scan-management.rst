Scan Management
===============

The scan management endpoints handle the complete lifecycle of security scans.

Create Scan
-----------

.. http:post:: /api/v1/scans

   Create a new security scan for a language model.

   **Required permissions:** write

   **Rate limit:** 10 requests/minute

   **Request:**

   .. sourcecode:: json

      {
        "generator": "openai",
        "model_name": "gpt-3.5-turbo",
        "probe_categories": ["dan", "promptinject"],
        "api_keys": {
          "openai_api_key": "sk-..."
        },
        "name": "GPT-3.5 Security Test",
        "description": "Testing for DAN attacks and security vulnerabilities",
        "parallel_attempts": 2
      }

   **Parameters:**

   .. list-table::
      :header-rows: 1

      * - Field
        - Type  
        - Required
        - Description
      * - generator
        - string
        - ✓
        - Model generator (openai, huggingface, etc.)
      * - model_name
        - string
        - ✓
        - Specific model to test
      * - probe_categories
        - array
        - ✗
        - Probe categories (dan, promptinject, etc.)
      * - probes
        - array
        - ✗
        - Specific probes (overrides categories)
      * - api_keys
        - object
        - ✗
        - API keys for external services
      * - name
        - string
        - ✗
        - Human-readable scan name
      * - description
        - string
        - ✗
        - Scan description
      * - parallel_attempts
        - integer
        - ✗
        - Parallel attempts (1-10, default: 1)

   **Response:**

   .. sourcecode:: json

      {
        "scan_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "message": "Scan created successfully",
        "metadata": {
          "scan_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
          "name": "GPT-3.5 Security Test",
          "status": "pending",
          "created_at": "2024-01-15T10:30:00Z",
          "generator": "openai",
          "model_name": "gpt-3.5-turbo",
          "probes": ["dan.Dan_11_0", "promptinject.HijackKillHumans"]
        }
      }

   **Status Codes:**

   * **201** - Scan created successfully
   * **400** - Invalid request parameters
   * **403** - Insufficient permissions
   * **429** - Rate limit exceeded

List Scans
----------

.. http:get:: /api/v1/scans

   Get a paginated list of all security scans.

   **Required permissions:** read

   **Rate limit:** 100 requests/minute

   **Query Parameters:**

   .. list-table::
      :header-rows: 1

      * - Parameter
        - Type
        - Description
      * - page
        - integer
        - Page number (default: 1)
      * - per_page
        - integer
        - Items per page (max: 100, default: 20)
      * - status
        - string
        - Filter by status (pending, running, completed, failed)

   **Example Request:**

   .. sourcecode:: bash

      curl -H "X-API-Key: your_key" \
           "http://localhost:8080/api/v1/scans?page=1&status=completed"

   **Response:**

   .. sourcecode:: json

      {
        "scans": [
          {
            "scan_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "name": "GPT-3.5 Security Test",
            "generator": "openai",
            "model_name": "gpt-3.5-turbo",
            "status": "completed",
            "created_at": "2024-01-15T10:30:00Z",
            "completed_at": "2024-01-15T10:45:00Z"
          }
        ],
        "total": 25,
        "page": 1,
        "per_page": 20,
        "has_next": true
      }

Get Scan Details
----------------

.. http:get:: /api/v1/scans/(str:scan_id)

   Get detailed information about a specific scan including results and reports.

   **Required permissions:** read

   **Rate limit:** 200 requests/minute

   **Response:**

   .. sourcecode:: json

      {
        "metadata": {
          "scan_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
          "name": "GPT-3.5 Security Test",
          "status": "completed",
          "created_at": "2024-01-15T10:30:00Z",
          "completed_at": "2024-01-15T10:45:30Z",
          "duration_seconds": 915.5,
          "generator": "openai",
          "model_name": "gpt-3.5-turbo",
          "probes": ["dan.Dan_11_0", "promptinject.HijackKillHumans"]
        },
        "results": {
          "total_probes": 15,
          "total_attempts": 30,
          "failed_attempts": 3,
          "success_rate": 90.0,
          "key_findings": [
            "Model showed some susceptibility to DAN attacks",
            "Strong resistance to prompt injection attempts"
          ]
        },
        "reports": [
          {
            "type": "json",
            "file_size": 45829,
            "created_at": "2024-01-15T10:45:30Z",
            "download_url": "/api/v1/scans/a1b2c3d4-e5f6-7890-abcd-ef1234567890/reports/json"
          }
        ]
      }

Get Scan Status
---------------

.. http:get:: /api/v1/scans/(str:scan_id)/status

   Get the current status of a scan (lightweight endpoint for polling).

   **Required permissions:** read

   **Rate limit:** 300 requests/minute

   **Response:**

   .. sourcecode:: json

      {
        "scan_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "status": "running",
        "progress": {
          "completed_items": 8,
          "total_items": 15,
          "progress_percent": 53.3,
          "elapsed_time": "2m 30s",
          "estimated_remaining": "2m 15s"
        },
        "created_at": "2024-01-15T10:30:00Z",
        "started_at": "2024-01-15T10:30:15Z"
      }

Get Scan Progress
-----------------

.. http:get:: /api/v1/scans/(str:scan_id)/progress

   Get detailed progress information for a running scan.

   **Required permissions:** read

   **Rate limit:** 500 requests/minute

   **Response:**

   .. sourcecode:: json

      {
        "status": "running",
        "progress": 65,
        "completed": false,
        "completed_items": 10,
        "total_items": 15,
        "elapsed_time": "3m 45s",
        "time_remaining": "1m 50s",
        "output": "Running probe: dan.Dan_11_0\nGenerating responses...\n..."
      }

Update Scan
-----------

.. http:patch:: /api/v1/scans/(str:scan_id)

   Update scan metadata (name and description only).

   **Required permissions:** write

   **Rate limit:** 50 requests/minute

   **Request:**

   .. sourcecode:: json

      {
        "name": "Updated Scan Name", 
        "description": "Updated description"
      }

   **Response:**

   .. sourcecode:: json

      {
        "message": "Scan updated successfully",
        "metadata": {
          "scan_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
          "name": "Updated Scan Name",
          "description": "Updated description"
        }
      }

Cancel Scan
-----------

.. http:delete:: /api/v1/scans/(str:scan_id)

   Cancel a running or pending scan.

   **Required permissions:** write

   **Rate limit:** 20 requests/minute

   **Response:**

   .. sourcecode:: json

      {
        "message": "Scan a1b2c3d4-e5f6-7890-abcd-ef1234567890 has been cancelled",
        "status": "cancelled"
      }

   .. note::
      Cancelled scans cannot be restarted. You will need to create a new scan.

Scan Status Flow
----------------

Scans progress through the following states:

.. code-block:: text

   pending → running → completed
       ↓       ↓         ↓
   cancelled   failed    (reports available)

* **pending** - Scan created, waiting to start
* **running** - Scan is actively executing probes  
* **completed** - Scan finished successfully, reports available
* **failed** - Scan encountered errors and stopped
* **cancelled** - Scan was manually cancelled

Error Handling
--------------

Common error scenarios:

**Scan Not Found (404)**
  The scan ID doesn't exist or you don't have permission to access it.

**Invalid Generator/Model (400)**
  The specified generator or model name is not available.

**Missing API Keys (400)**
  External API keys are required for the specified generator.

**Scan Already Running (409)**
  Cannot modify a scan that is currently running.