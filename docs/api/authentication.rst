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

API Key Formats
---------------

API keys have the following characteristics:

* **Format**: ``garak_{32_random_bytes}``
* **Storage**: SHA256 hashed in database
* **Identification**: First 8 characters used for display

Authentication Methods
----------------------

Header Authentication (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Authorization header (recommended)
   curl -H "Authorization: Bearer garak_abc123..." \
        http://localhost:8080/api/v1/health

   # X-API-Key header
   curl -H "X-API-Key: garak_abc123..." \
        http://localhost:8080/api/v1/health

Query Parameter Authentication
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. warning::
   Query parameter authentication is less secure and not recommended for production use.

.. code-block:: bash

   curl "http://localhost:8080/api/v1/health?api_key=garak_abc123..."

Bootstrap Setup
---------------

For first-time setup, create an initial admin API key:

.. code-block:: bash

   curl -X POST http://localhost:8080/api/v1/admin/bootstrap

This endpoint is only available when no admin keys exist in the system.

Response:

.. code-block:: json

   {
     "api_key": "garak_admin_abc123...",
     "message": "Bootstrap admin key created successfully. Store this key securely.",
     "key_info": {
       "id": 1,
       "key_prefix": "garak_admin_abc",
       "name": "Initial Admin Key",
       "permissions": ["read", "write", "admin"]
     }
   }

Creating Additional Keys
------------------------

Use your admin key to create additional keys with appropriate permissions:

.. code-block:: bash

   curl -X POST http://localhost:8080/api/v1/admin/api-keys \
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

   curl -X GET http://localhost:8080/api/v1/admin/api-keys \
        -H "X-API-Key: your_admin_key"

Revoke API Key
~~~~~~~~~~~~~~

.. code-block:: bash

   curl -X POST http://localhost:8080/api/v1/admin/api-keys/123/revoke \
        -H "X-API-Key: your_admin_key"

Delete API Key
~~~~~~~~~~~~~~

.. code-block:: bash

   curl -X DELETE http://localhost:8080/api/v1/admin/api-keys/123 \
        -H "X-API-Key: your_admin_key"