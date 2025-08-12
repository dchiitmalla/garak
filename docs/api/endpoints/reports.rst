Report Management
=================

Download scan results and reports.

List Reports
------------

.. http:get:: /api/v1/scans/(str:scan_id)/reports

   List available reports for a completed scan.

   **Rate limit:** 100 requests/minute

   .. code-block:: bash

      curl -H "X-API-Key: your_api_key_here" \
           https://your-api-domain.com/api/v1/scans/{scan_id}/reports

   **Response:**

   .. code-block:: json

      {
        "scan_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "reports": [
          {
            "type": "json",
            "created_at": "2024-01-15T10:45:30Z"
          },
          {
            "type": "html",
            "created_at": "2024-01-15T10:45:32Z"
          }
        ]
      }

Download JSON Report
--------------------

.. http:get:: /api/v1/scans/(str:scan_id)/reports/json

   Download structured JSON report.

   **Rate limit:** 50 requests/minute

   .. code-block:: bash

      curl -H "X-API-Key: your_api_key_here" \
           https://your-api-domain.com/api/v1/scans/{scan_id}/reports/json \
           -o scan_report.json

Download HTML Report
--------------------

.. http:get:: /api/v1/scans/(str:scan_id)/reports/html

   Download visual HTML report.

   **Rate limit:** 50 requests/minute

   .. code-block:: bash

      curl -H "X-API-Key: your_api_key_here" \
           https://your-api-domain.com/api/v1/scans/{scan_id}/reports/html \
           -o scan_report.html

Download JSONL Report
---------------------

.. http:get:: /api/v1/scans/(str:scan_id)/reports/jsonl

   Download line-delimited JSON report.

   **Rate limit:** 50 requests/minute

   .. code-block:: bash

      curl -H "X-API-Key: your_api_key_here" \
           https://your-api-domain.com/api/v1/scans/{scan_id}/reports/jsonl \
           -o scan_report.jsonl

Download Hits Report
--------------------

.. http:get:: /api/v1/scans/(str:scan_id)/reports/hits

   Download security violations only.

   **Rate limit:** 50 requests/minute

   .. code-block:: bash

      curl -H "X-API-Key: your_api_key_here" \
           https://your-api-domain.com/api/v1/scans/{scan_id}/reports/hits \
           -o scan_hits.json

Report Types
------------

* **JSON** - Structured data for programmatic analysis
* **HTML** - Visual report with charts for security reviews
* **JSONL** - Line-delimited JSON for data processing  
* **Hits** - Security violations only

Status Codes
------------

* **200** - Report downloaded successfully
* **404** - Report not found or scan not completed
* **400** - Invalid report type
* **429** - Rate limit exceeded

Notes
-----

* **Only completed scans** have reports available
* **Generated automatically** within 30 seconds of scan completion
* **All report types** available simultaneously
* **Use appropriate format** for your use case