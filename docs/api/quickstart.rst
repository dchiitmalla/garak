Quick Start
===========

This guide gets you started with the Garak Scans API in minutes.

Base URL
--------

All API requests are made to:

.. code-block:: text

   https://your-api-domain.com/api/v1

Replace ``your-api-domain.com`` with your actual API endpoint.

Step 1: Get an API Key
----------------------

Create your first admin API key:

.. code-block:: bash

   curl -X POST https://your-api-domain.com/api/v1/admin/bootstrap

Save the returned API key securely - you'll need it for all future requests.

Step 2: Test API Access
-----------------------

Verify your API key works:

.. code-block:: bash

   export API_KEY="your_api_key_here"
   curl -H "X-API-Key: $API_KEY" https://your-api-domain.com/api/v1/health

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

   curl -H "X-API-Key: $API_KEY" https://your-api-domain.com/api/v1/generators

List available security probes:

.. code-block:: bash

   curl -H "X-API-Key: $API_KEY" https://your-api-domain.com/api/v1/probes

Step 4: Create Your First Scan
-------------------------------

Create a security scan of GPT-2 for hallucination vulnerabilities:

.. code-block:: bash

   curl -X POST https://your-api-domain.com/api/v1/scans \
        -H "X-API-Key: $API_KEY" \
        -H "Content-Type: application/json" \
        -d '{
          "generator": "huggingface",
          "model_name": "gpt2", 
          "probe_categories": ["hallucination"],
          "name": "My First Security Scan",
          "description": "Testing GPT-2 for hallucination vulnerabilities"
        }'

For models requiring API access, include the ``api_keys`` field:

.. code-block:: bash

   curl -X POST https://your-api-domain.com/api/v1/scans \
        -H "X-API-Key: $API_KEY" \
        -H "Content-Type: application/json" \
        -d '{
          "generator": "openai",
          "model_name": "gpt-3.5-turbo",
          "probe_categories": ["hallucination"],
          "name": "OpenAI Security Scan", 
          "description": "Testing GPT-3.5 for vulnerabilities",
          "api_keys": {
            "openai_api_key": "sk-your_openai_key_here"
          }
        }'

**API Keys**: 

- **Local models** (``huggingface`` with ``gpt2``, etc.): Run directly without API keys
- **Cloud providers**: Require API keys, but will fall back to **test mode** with HuggingFace GPT-2 if missing  

**Get API tokens**:

- `OpenAI <https://platform.openai.com/api-keys>`_ (``openai_api_key``)
- `Anthropic <https://console.anthropic.com/>`_ (``anthropic_api_key``) 
- `HuggingFace <https://huggingface.co/settings/tokens>`_ (``huggingface_api_key``)
- `Cohere <https://dashboard.cohere.ai/api-keys>`_ (``cohere_api_key``)
- `Google AI <https://makersuite.google.com/app/apikey>`_ (``google_api_key`` for Gemini)
- `Mistral AI <https://console.mistral.ai/>`_ (``mistral_api_key``)
- `Replicate <https://replicate.com/account/api-tokens>`_ (``replicate_api_token``)
- `Google Cloud <https://console.cloud.google.com/apis/credentials>`_ (``gcp_credentials_path`` for VertexAI)

The response includes a ``scan_id`` for tracking the scan.

Step 5: Monitor Scan Progress
-----------------------------

Check scan status (replace ``{scan_id}`` with your actual scan ID from Step 4):

.. code-block:: bash

   curl -H "X-API-Key: $API_KEY" \
        https://your-api-domain.com/api/v1/scans/{scan_id}/status

Get detailed progress:

.. code-block:: bash

   curl -H "X-API-Key: $API_KEY" \
        https://your-api-domain.com/api/v1/scans/{scan_id}/progress

Step 6: Download Results
------------------------

Once the scan completes, download the report:

.. code-block:: bash

   # JSON report
   curl -H "X-API-Key: $API_KEY" \
        https://your-api-domain.com/api/v1/scans/{scan_id}/reports/json \
        -o scan_report.json

   # HTML report  
   curl -H "X-API-Key: $API_KEY" \
        https://your-api-domain.com/api/v1/scans/{scan_id}/reports/html \
        -o scan_report.html

Next Steps
----------

* Read the :doc:`endpoints/index` for complete API reference
* Try :doc:`examples` with different models and probe combinations  
* Review :doc:`rate-limiting` for API usage limits and :doc:`error-handling` for robust error management
* Optional: Use the :doc:`python-sdk` for Python applications (or build your own HTTP client)

Common Issues
-------------

**HTTP 401 Unauthorized**
  Your API key is missing or invalid. Ensure your key starts with ``garak_`` and is included in the ``X-API-Key`` header.

**HTTP 400 Bad Request**  
  Invalid request parameters. Use ``/api/v1/generators`` and ``/api/v1/probes`` to check valid values.

**Scan fails immediately**
  Missing API keys for cloud providers. Check the logs in the progress endpoint for specific error messages.

**HTTP 429 Too Many Requests**
  You've exceeded the rate limit. Wait and retry, or contact support to increase your limits.