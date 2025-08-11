Garak Scans API Reference
=========================

The Garak Dashboard API provides programmatic access to LLM security scanning capabilities.

.. note::
   This API documentation is under active development. Let us know if there's anything
   wrong, confusing, or missing by emailing docs@garak.ai

Quick Links
-----------

* `User Guide <https://docs.garak.ai>`_
* `Discord <https://discord.gg/uVch4puUCs>`_  
* `Twitter <https://twitter.com/garak_llm>`_

Overview
--------

The Garak Scans API is a RESTful interface that enables developers to integrate AI red-teaming 
capabilities into their workflows. The API allows you to create, monitor, and manage security 
scans of language models, testing for vulnerabilities including jailbreaking attacks, prompt 
injection, data leakage, toxicity generation, and other security weaknesses.

.. toctree::
   :maxdepth: 2
   :caption: Using the API

   authentication
   quickstart
   endpoints/index
   examples
   
.. toctree::
   :maxdepth: 2
   :caption: API Reference
   
   endpoints/scan-management
   endpoints/discovery
   endpoints/admin
   endpoints/reports
   
.. toctree::
   :maxdepth: 2
   :caption: Advanced Usage
   
   error-handling
   rate-limiting
   python-sdk
   best-practices
   
.. toctree::
   :maxdepth: 1
   :caption: Deployment
   
   deployment/local
   deployment/docker
   deployment/cloud