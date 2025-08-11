Quick Start
===========

This guide gets you started with the Garak Scans API in minutes.

Prerequisites
-------------

* Python 3.8 or higher
* Access to language model APIs (OpenAI, etc.) or local models
* Garak installed and configured

Base URL
--------

All API requests are made to:

.. code-block:: text

   http://localhost:8080/api/v1

Replace ``localhost:8080`` with your server's address.

Step 1: Get an API Key
----------------------

Create your first admin API key:

.. code-block:: bash

   curl -X POST http://localhost:8080/api/v1/admin/bootstrap

Save the returned API key securely - you'll need it for all future requests.

Step 2: Test API Access
-----------------------

Verify your API key works:

.. code-block:: bash

   export API_KEY="garak_your_api_key_here"
   curl -H "X-API-Key: $API_KEY" http://localhost:8080/api/v1/health

Expected response:

.. code-block:: json

   {
     "status": "healthy",
     "version": "1.0.0",
     "services": {
       "database": "healthy",
       "job_system": "healthy"
     }
   }

Step 3: Discover Available Options
----------------------------------

List available model generators:

.. code-block:: bash

   curl -H "X-API-Key: $API_KEY" http://localhost:8080/api/v1/generators

List available security probes:

.. code-block:: bash

   curl -H "X-API-Key: $API_KEY" http://localhost:8080/api/v1/probes

Step 4: Create Your First Scan
-------------------------------

Create a security scan of GPT-2 for hallucination vulnerabilities:

.. code-block:: bash

   curl -X POST http://localhost:8080/api/v1/scans \
        -H "X-API-Key: $API_KEY" \
        -H "Content-Type: application/json" \
        -d '{
          "generator": "huggingface",
          "model_name": "gpt2",
          "probe_categories": ["hallucination"],
          "name": "My First Security Scan",
          "description": "Testing GPT-2 for hallucination vulnerabilities"
        }'

The response includes a ``scan_id`` for tracking the scan.

Step 5: Monitor Scan Progress
-----------------------------

Check scan status:

.. code-block:: bash

   curl -H "X-API-Key: $API_KEY" \
        http://localhost:8080/api/v1/scans/{scan_id}/status

Get detailed progress:

.. code-block:: bash

   curl -H "X-API-Key: $API_KEY" \
        http://localhost:8080/api/v1/scans/{scan_id}/progress

Step 6: Download Results
------------------------

Once the scan completes, download the report:

.. code-block:: bash

   # JSON report
   curl -H "X-API-Key: $API_KEY" \
        http://localhost:8080/api/v1/scans/{scan_id}/reports/json \
        -o scan_report.json

   # HTML report  
   curl -H "X-API-Key: $API_KEY" \
        http://localhost:8080/api/v1/scans/{scan_id}/reports/html \
        -o scan_report.html

Next Steps
----------

* Explore the :doc:`endpoints/index` for advanced options
* Try different :doc:`examples` with various models and probes  
* Set up :doc:`python-sdk` for programmatic access
* Review :doc:`best-practices` for production usage

Common Issues
-------------

**Port already in use**
  Change the port: ``python app.py --port 8081``

**Authentication errors**
  Verify your API key format starts with ``garak_``

**Scan creation fails**
  Check that the generator and model_name are valid using the discovery endpoints