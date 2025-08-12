Garak Security API Documentation
================================

This directory contains the complete API reference documentation for the Garak Security Scans API,
following the same structure and format as the main Garak project documentation.

Building the Documentation
--------------------------

This documentation is built using Sphinx and follows the Read the Docs theme used
by the main Garak project.

Prerequisites
~~~~~~~~~~~~~

Install Sphinx and required extensions:

.. code-block:: bash

   pip install sphinx sphinx_rtd_theme sphinxcontrib-httpdomain

Building HTML Documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   cd docs/api
   sphinx-build -b html . _build/html

The generated documentation will be available in ``_build/html/index.html``.

Building for Read the Docs
~~~~~~~~~~~~~~~~~~~~~~~~~~~

This documentation is structured to be compatible with Read the Docs hosting:

.. code-block:: bash

   # Build with Read the Docs theme
   sphinx-build -b html -D html_theme=sphinx_rtd_theme . _build/html

Documentation Structure
-----------------------

The documentation is organized into the following sections:

**Using the API**
* :doc:`authentication` - API key setup and management
* :doc:`quickstart` - Getting started guide
* :doc:`endpoints/index` - Complete endpoint reference
* :doc:`examples` - Practical usage examples

**API Reference**
* :doc:`endpoints/scan-management` - Scan lifecycle management
* :doc:`endpoints/discovery` - Capability discovery
* :doc:`endpoints/admin` - Administrative operations  
* :doc:`endpoints/reports` - Report download and management

**Usage Tips**
* :doc:`error-handling` - Error codes and troubleshooting
* :doc:`rate-limiting` - Understanding and managing rate limits
* :doc:`python-sdk` - Using the Python SDK
* :doc:`best-practices` - Best practices for API usage

**Deployment**
* :doc:`deployment/local` - Local development setup
* :doc:`deployment/docker` - Container deployment
* :doc:`deployment/cloud` - Cloud platform deployment

File Organization
-----------------

.. code-block:: text

   docs/api/
   ├── index.rst              # Main documentation index
   ├── conf.py               # Sphinx configuration
   ├── authentication.rst   # Authentication guide
   ├── quickstart.rst       # Quick start guide
   ├── python-sdk.rst       # Python SDK documentation
   ├── endpoints/           # API endpoint reference
   │   ├── index.rst
   │   ├── scan-management.rst
   │   ├── discovery.rst
   │   ├── reports.rst
   │   └── admin.rst
   └── _build/              # Generated documentation output

Consistency with Main Documentation
-----------------------------------

This API documentation follows the same patterns as the main Garak documentation:

* **Theme**: Uses ``sphinx_rtd_theme`` for consistency
* **Structure**: Hierarchical organization with clear navigation
* **Style**: Technical reference with practical examples
* **Format**: RST (reStructuredText) with Sphinx extensions

The documentation integrates seamlessly with the main Garak docs and can be
linked from the primary documentation site.

Contributing
------------

When updating the API documentation:

1. **Follow RST syntax** for consistency with main docs
2. **Include code examples** for all endpoints
3. **Update cross-references** when adding new sections
4. **Test documentation builds** before submitting changes
5. **Maintain the hierarchical structure** established in the index

For questions about the documentation structure or content, contact the
Garak Security team at docs@getgarak.com.

----

Copyright © Garak Security Team. All rights reserved.