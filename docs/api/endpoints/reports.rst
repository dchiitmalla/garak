Report Management
=================

Report management endpoints provide access to scan results and generated reports.

List Available Reports
----------------------

.. http:get:: /api/v1/scans/(str:scan_id)/reports

   List all available reports for a completed scan.

   **Required permissions:** read

   **Rate limit:** 100 requests/minute

   **Response:**

   .. sourcecode:: json

      {
        "scan_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "reports": [
          {
            "type": "json",
            "file_size": 45829,
            "created_at": "2024-01-15T10:45:30Z",
            "download_url": "/api/v1/scans/a1b2c3d4-e5f6-7890-abcd-ef1234567890/reports/json"
          },
          {
            "type": "html", 
            "file_size": 892134,
            "created_at": "2024-01-15T10:45:32Z",
            "download_url": "/api/v1/scans/a1b2c3d4-e5f6-7890-abcd-ef1234567890/reports/html"
          },
          {
            "type": "jsonl",
            "file_size": 156728,
            "created_at": "2024-01-15T10:45:31Z", 
            "download_url": "/api/v1/scans/a1b2c3d4-e5f6-7890-abcd-ef1234567890/reports/jsonl"
          },
          {
            "type": "hits",
            "file_size": 23456,
            "created_at": "2024-01-15T10:45:31Z",
            "download_url": "/api/v1/scans/a1b2c3d4-e5f6-7890-abcd-ef1234567890/reports/hits"
          }
        ]
      }

Download Report
---------------

.. http:get:: /api/v1/scans/(str:scan_id)/reports/(str:report_type)

   Download a specific report file.

   **Required permissions:** read

   **Rate limit:** 50 requests/minute

   **Parameters:**

   .. list-table::
      :header-rows: 1

      * - Parameter
        - Type
        - Description
      * - scan_id
        - string
        - Unique scan identifier
      * - report_type
        - string
        - Report format (json, html, jsonl, hits)

   **Example Requests:**

   .. sourcecode:: bash

      # Download JSON report
      curl -H "X-API-Key: your_key" \
           http://localhost:8080/api/v1/scans/a1b2c3d4-e5f6-7890-abcd-ef1234567890/reports/json \
           -o scan_report.json

      # Download HTML report
      curl -H "X-API-Key: your_key" \
           http://localhost:8080/api/v1/scans/a1b2c3d4-e5f6-7890-abcd-ef1234567890/reports/html \
           -o scan_report.html

   **Response:**
   
   Returns the raw report file content with appropriate Content-Type header.

Report Types
------------

JSON Report
~~~~~~~~~~~

**Format:** ``application/json``

Detailed structured results including:

* Complete scan metadata
* Individual probe results with attempts
* Detector evaluations and scores
* Statistical summaries
* Timing information

**Use case:** Programmatic analysis, data processing, integration with other tools

HTML Report  
~~~~~~~~~~~

**Format:** ``text/html``

Human-readable report with:

* Executive summary
* Visual charts and graphs
* Detailed findings by probe category
* Risk assessment and recommendations
* Interactive elements for exploration

**Use case:** Management reporting, security reviews, documentation

JSONL Report
~~~~~~~~~~~~

**Format:** ``application/x-ndjson``

Line-delimited JSON with one attempt per line:

* Streaming-friendly format
* Easier to process large datasets
* Compatible with big data tools
* Individual attempt records

**Use case:** Data analysis, machine learning, log processing

Hits Report
~~~~~~~~~~~

**Format:** ``application/json``

Filtered results showing only security violations:

* Failed detector evaluations only
* Critical findings highlighted  
* Reduced file size
* Security-focused summary

**Use case:** Security alerting, vulnerability assessment, compliance reporting

Report Availability
-------------------

Reports are generated automatically when scans complete successfully.

**Generation Timeline:**

1. Scan completes with status ``completed``
2. Report generation begins immediately
3. All report types generated in parallel
4. Reports become available within 30 seconds

**Retention Policy:**

* Reports stored for 90 days by default
* Can be configured per deployment
* Download reports promptly for long-term storage

**File Sizes:**

Typical report sizes vary by scan scope:

.. list-table::
   :header-rows: 1

   * - Report Type
     - Small Scan
     - Medium Scan
     - Large Scan
   * - JSON
     - 1-10 KB
     - 50-500 KB
     - 1-10 MB
   * - HTML
     - 10-100 KB
     - 500 KB-5 MB
     - 5-50 MB
   * - JSONL
     - 1-50 KB
     - 100 KB-1 MB
     - 1-20 MB
   * - Hits
     - < 1 KB
     - 1-10 KB
     - 10-100 KB

Error Handling
--------------

**Report Not Ready (404)**

Reports are not available until scan completion:

.. sourcecode:: json

   {
     "error": "report_not_found",
     "message": "Reports are not available for pending/running scans"
   }

**Report Generation Failed (500)**

If report generation encounters errors:

.. sourcecode:: json

   {
     "error": "report_generation_failed", 
     "message": "Report generation failed due to processing error"
   }

**Invalid Report Type (400)**

When requesting unsupported report format:

.. sourcecode:: json

   {
     "error": "invalid_report_type",
     "message": "Supported types: json, html, jsonl, hits"
   }

Best Practices
--------------

**Performance:**
* Use ``hits`` format for security-focused analysis
* Use ``jsonl`` for large dataset processing
* Cache downloaded reports to avoid repeated requests

**Storage:**
* Download critical reports immediately after scan completion
* Implement local backup strategy for compliance requirements
* Use appropriate compression for long-term storage

**Analysis:**
* Use JSON format for automated processing and alerts
* Use HTML format for human review and reporting
* Combine multiple report types for comprehensive analysis