Authentication
==============

All API endpoints require authentication using API keys. This page describes how to obtain
and use API keys for accessing the Garak Scans API.

API Key Types
-------------

The API supports different permission levels:

* **read** - Can view scans, generators, and probes
* **write** - Can create and modify scans  
* **admin** - Full system access including API key management

Authentication Methods
----------------------

Header Authentication
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Authorization header
   curl -H "Authorization: Bearer your_api_key_here" \
        https://your-api-domain.com/api/v1/health

   # X-API-Key header
   curl -H "X-API-Key: your_api_key_here" \
        https://your-api-domain.com/api/v1/health

Query Parameter Authentication
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


.. code-block:: bash

   curl "https://your-api-domain.com/api/v1/health?api_key=your_api_key_here"

Bootstrap Setup
---------------

For first-time setup, create an initial admin API key:

.. code-block:: bash

   curl -X POST https://your-api-domain.com/api/v1/admin/bootstrap

This endpoint is only available when no admin keys exist in the system.

Response:

.. code-block:: json

   {
     "api_key": "your_admin_api_key_here",
     "key_info": {
       "id": 1,
       "key_prefix": "your_key_prefix",
       "name": "Initial Admin Key",
       "permissions": ["read", "write", "admin"]
     },
     "message": "Bootstrap admin key created successfully. Store this key securely - it will not be shown again.",
     "next_steps": [
       "Store the API key in a secure location",
       "Use this key to create additional API keys with appropriate permissions",
       "Consider setting up rate limiting and monitoring"
     ]
   }

Creating Additional Keys
------------------------

Use your admin key to create additional keys with appropriate permissions:

.. code-block:: bash

   curl -X POST https://your-api-domain.com/api/v1/admin/api-keys \
        -H "X-API-Key: your_admin_key" \
        -H "Content-Type: application/json" \
        -d '{
          "name": "Scan API Key",
          "description": "For automated security scans", 
          "permissions": ["read", "write"],
          "rate_limit": 100,
          "expires_days": 90
        }'

Development Mode
----------------

For development and testing, authentication can be disabled:

.. code-block:: bash

   export DISABLE_AUTH=true

.. warning::
   Never disable authentication in production environments.

Key Management
--------------

List API Keys
~~~~~~~~~~~~~

.. code-block:: bash

   curl -X GET https://your-api-domain.com/api/v1/admin/api-keys \
        -H "X-API-Key: your_admin_key"

Revoke API Key
~~~~~~~~~~~~~~

.. code-block:: bash

   curl -X POST https://your-api-domain.com/api/v1/admin/api-keys/123/revoke \
        -H "X-API-Key: your_admin_key"

Delete API Key
~~~~~~~~~~~~~~

.. code-block:: bash

   curl -X DELETE https://your-api-domain.com/api/v1/admin/api-keys/123 \
        -H "X-API-Key: your_admin_key"