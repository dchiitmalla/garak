API Keys Reference
==================

This page explains how to use API keys for different generators when creating security scans.

Overview
--------

When creating scans, you need to provide API keys for the model generators you want to test. The ``api_keys`` field in scan requests accepts different key names depending on the generator.

API Key Field Names by Generator
---------------------------------

Required API Keys
~~~~~~~~~~~~~~~~~

The following generators require API keys:

**OpenAI**
   - Field name: ``openai_api_key``
   - Example: ``"openai_api_key": "sk-your-openai-key-here"``
   - Used for: GPT-3.5, GPT-4, and other OpenAI models

**Anthropic Claude**
   - Field name: ``anthropic_api_key``
   - Example: ``"anthropic_api_key": "sk-ant-your-key-here"``
   - Used for: Claude models via LiteLLM

**Cohere**
   - Field name: ``cohere_api_key``
   - Example: ``"cohere_api_key": "your-cohere-key-here"``
   - Used for: Cohere Command models

**Replicate**
   - Field name: ``replicate_api_token``
   - Example: ``"replicate_api_token": "r8_your-token-here"``
   - Used for: Models hosted on Replicate platform

**Mistral AI**
   - Field name: ``mistral_api_key``
   - Example: ``"mistral_api_key": "your-mistral-key-here"``
   - Used for: Mistral models

**Google Vertex AI**
   - Field name: ``google_api_key``
   - Example: ``"google_api_key": "your-google-key-here"``
   - Used for: Google Cloud Vertex AI models

**LiteLLM**
   - Field name: ``litellm_api_key``
   - Example: ``"litellm_api_key": "your-key-here"``
   - Used for: Universal LLM interface

Optional/Local Generators
~~~~~~~~~~~~~~~~~~~~~~~~~

The following generators are optional or run locally:

**Hugging Face**
   - Field name: ``hf_inference_token`` (optional)
   - Example: ``"hf_inference_token": "hf_your-token-here"``
   - Used for: Open source models from Hugging Face Hub
   - Note: Token is optional for public models

**Ollama**
   - No API key required (runs locally)
   - Used for: Local models via Ollama

**Llama.cpp**
   - No API key required (runs locally)
   - Used for: Local GGML/GGUF models

Usage Examples
--------------

Single Generator Example
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   curl -X POST https://your-api-domain.com/api/v1/scans \\
     -H "X-API-Key: your_api_key_here" \\
     -H "Content-Type: application/json" \\
     -d '{
       "generator": "openai",
       "model_name": "gpt-3.5-turbo",
       "probe_categories": ["dan", "security"],
       "api_keys": {
         "openai_api_key": "sk-your-openai-key-here"
       },
       "name": "OpenAI Security Test"
     }'

Multiple Generators with LiteLLM
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   curl -X POST https://your-api-domain.com/api/v1/scans \\
     -H "X-API-Key: your_api_key_here" \\
     -H "Content-Type: application/json" \\
     -d '{
       "generator": "litellm",
       "model_name": "gpt-3.5-turbo",
       "probe_categories": ["dan"],
       "api_keys": {
         "openai_api_key": "sk-...",
         "anthropic_api_key": "sk-ant-...",
         "cohere_api_key": "...",
         "replicate_api_token": "r8_...",
         "mistral_api_key": "...",
         "google_api_key": "..."
       },
       "name": "Multi-Provider Test"
     }'

Local Generators (No API Keys)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   curl -X POST https://your-api-domain.com/api/v1/scans \\
     -H "X-API-Key: your_api_key_here" \\
     -H "Content-Type: application/json" \\
     -d '{
       "generator": "huggingface",
       "model_name": "gpt2",
       "probe_categories": ["toxicity"],
       "name": "HuggingFace Local Test"
     }'

Python Example
~~~~~~~~~~~~~~

.. code-block:: python

   import requests

   # API configuration
   API_BASE = "https://your-api-domain.com/api/v1"
   headers = {
       "X-API-Key": "your_api_key_here",
       "Content-Type": "application/json"
   }

   # Scan with multiple API keys
   scan_data = {
       "generator": "openai",
       "model_name": "gpt-4",
       "probe_categories": ["dan", "security"],
       "api_keys": {
           "openai_api_key": "sk-your-openai-key-here"
       },
       "name": "GPT-4 Security Assessment"
   }

   response = requests.post(f"{API_BASE}/scans", json=scan_data, headers=headers)
   scan_id = response.json()["scan_id"]
   print(f"Created scan: {scan_id}")

Discovery
---------

To see all available generators and their requirements programmatically:

.. code-block:: bash

   curl -H "X-API-Key: your_api_key_here" \\
        https://your-api-domain.com/api/v1/generators

This will return detailed information about each generator including whether it requires an API key.

Common Issues
-------------

**Missing API Key**
   If you forget to include the required API key for a generator, the scan will fail with an authentication error.

**Wrong Key Name**
   Using incorrect field names (e.g., ``openai_key`` instead of ``openai_api_key``) will cause the key to be ignored.

**Invalid Key Format**
   Each provider has specific key formats. Ensure your keys match the expected format for each service.

See Also
--------

* :doc:`quickstart` - Getting started with the API
* :doc:`endpoints/scan-management` - Detailed scan management documentation
* :doc:`endpoints/discovery` - Discovery endpoints for available generators