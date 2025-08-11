Discovery Endpoints
==================

Discovery endpoints enable clients to discover available capabilities before creating scans.

List Generators
---------------

.. http:get:: /api/v1/generators

   List all available model generators and their capabilities.

   **Required permissions:** read

   **Rate limit:** 100 requests/minute

   **Response:**

   .. sourcecode:: json

      {
        "generators": [
          {
            "name": "openai",
            "display_name": "OpenAI",
            "description": "OpenAI models including GPT-3.5, GPT-4",
            "requires_api_key": true,
            "supported_models": [
              "gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"
            ]
          },
          {
            "name": "huggingface", 
            "display_name": "Hugging Face",
            "description": "Open source models from Hugging Face Hub",
            "requires_api_key": false,
            "supported_models": [
              "gpt2", "microsoft/DialoGPT-medium"
            ]
          }
        ],
        "total": 11
      }

Get Generator Details
--------------------

.. http:get:: /api/v1/generators/(str:generator_name)

   Get detailed information about a specific generator.

   **Response:**

   .. sourcecode:: json

      {
        "name": "openai",
        "display_name": "OpenAI", 
        "description": "OpenAI models including GPT-3.5, GPT-4",
        "requires_api_key": true,
        "supported_models": [
          "gpt-4", "gpt-4-turbo", "gpt-4o", "gpt-3.5-turbo"
        ],
        "configuration": {
          "api_key_required": true,
          "base_url_configurable": false,
          "supported_parameters": ["temperature", "max_tokens"]
        }
      }

List Generator Models
--------------------

.. http:get:: /api/v1/generators/(str:generator_name)/models

   List available models for a specific generator.

   **Response:**

   .. sourcecode:: json

      {
        "generator": "openai",
        "models": [
          {
            "name": "gpt-4",
            "display_name": "GPT-4",
            "description": "Most capable GPT-4 model"
          },
          {
            "name": "gpt-3.5-turbo",
            "display_name": "GPT-3.5 Turbo", 
            "description": "Fast and cost-effective model"
          }
        ],
        "total": 8
      }

List Probe Categories
--------------------

.. http:get:: /api/v1/probes

   List all probe categories and their individual probes.

   **Required permissions:** read

   **Rate limit:** 100 requests/minute

   **Response:**

   .. sourcecode:: json

      {
        "categories": [
          {
            "name": "dan",
            "display_name": "DAN (Do Anything Now)",
            "description": "Jailbreaking attacks that bypass safety guidelines",
            "probes": [
              {
                "name": "dan.Dan_11_0",
                "display_name": "Dan_11_0",
                "category": "dan",
                "description": "Security probe: dan.Dan_11_0"
              }
            ]
          },
          {
            "name": "security",
            "display_name": "Security Vulnerabilities", 
            "description": "Tests for prompt injection and security exploits",
            "probes": [
              {
                "name": "promptinject.HijackKillHumans",
                "display_name": "HijackKillHumans", 
                "category": "security",
                "description": "Security probe: promptinject.HijackKillHumans"
              }
            ]
          }
        ],
        "total_categories": 9,
        "total_probes": 156
      }

List Category Probes  
-------------------

.. http:get:: /api/v1/probes/(str:category_name)

   List all probes in a specific category.

   **Response:**

   .. sourcecode:: json

      {
        "category": "dan",
        "display_name": "DAN (Do Anything Now)",
        "description": "Jailbreaking attacks that bypass safety guidelines",
        "probes": [
          {
            "name": "dan.Dan_11_0",
            "display_name": "Dan_11_0",
            "description": "DAN jailbreak version 11.0"
          },
          {
            "name": "dan.Dan_6_0", 
            "display_name": "Dan_6_0",
            "description": "DAN jailbreak version 6.0"
          }
        ],
        "total": 15
      }

Supported Generators
-------------------

The API supports the following generator types:

.. list-table::
   :header-rows: 1

   * - Generator
     - Description
     - API Key Required
     - Local/Remote
   * - openai
     - OpenAI models (GPT-3.5, GPT-4)
     - ✓
     - Remote
   * - anthropic
     - Anthropic Claude models
     - ✓
     - Remote
   * - huggingface
     - Open source Hugging Face models
     - ✗
     - Both
   * - cohere
     - Cohere language models
     - ✓
     - Remote
   * - ollama
     - Local models via Ollama
     - ✗
     - Local
   * - replicate
     - Models on Replicate platform
     - ✓
     - Remote
   * - vertexai
     - Google Vertex AI models
     - ✓
     - Remote
   * - llamacpp
     - Local GGML/GGUF models
     - ✗
     - Local
   * - mistral
     - Mistral AI models
     - ✓
     - Remote
   * - litellm
     - Universal LLM interface
     - ✓
     - Remote
   * - rest
     - Custom REST endpoints
     - ✓
     - Remote

Probe Categories
----------------

The following probe categories are available:

.. list-table::
   :header-rows: 1

   * - Category
     - Description
     - Probe Count
   * - dan
     - DAN (Do Anything Now) jailbreaking attacks
     - 19
   * - security
     - Prompt injection and security exploits
     - 7
   * - privacy
     - Data leakage and memorization tests
     - 8
   * - toxicity
     - Harmful content generation
     - 9
   * - hallucination
     - Factual accuracy and misinformation
     - 5
   * - performance
     - Consistency and reliability
     - 5
   * - robustness
     - Adversarial input resistance
     - 5
   * - ethics
     - Bias and ethical considerations
     - 4
   * - stereotype
     - Stereotypical output detection
     - 1

Dynamic Discovery
-----------------

Generators and probes are discovered dynamically from the Garak core library.
This means:

* New generators added to Garak automatically appear in the API
* New probes are automatically available for selection
* The discovery endpoints always reflect the current Garak installation

.. note::
   Some generators may not be available if their dependencies are not installed.
   Check the generator's ``requires_api_key`` and configuration requirements.