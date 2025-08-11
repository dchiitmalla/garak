Python SDK
==========

A Python SDK for interacting with the Garak Scans API programmatically.

Installation
------------

The SDK requires Python 3.8+ and the ``requests`` library:

.. code-block:: bash

   pip install requests

Basic Usage
-----------

Here's a complete example of creating and monitoring a security scan:

.. code-block:: python

   import requests
   import time
   from typing import Dict, Any, Optional

   class GarakAPI:
       def __init__(self, base_url: str, api_key: str):
           """Initialize the Garak API client.
           
           Args:
               base_url: Base URL for the API (e.g., 'http://localhost:8080/api/v1')
               api_key: Your API key starting with 'garak_'
           """
           self.base_url = base_url.rstrip('/')
           self.headers = {
               "X-API-Key": api_key,
               "Content-Type": "application/json"
           }
       
       def create_scan(self, config: Dict[str, Any]) -> str:
           """Create a new security scan.
           
           Args:
               config: Scan configuration dictionary
               
           Returns:
               scan_id: Unique identifier for the created scan
               
           Raises:
               requests.HTTPError: If the API request fails
           """
           response = requests.post(
               f"{self.base_url}/scans",
               json=config,
               headers=self.headers
           )
           response.raise_for_status()
           return response.json()["scan_id"]
       
       def get_scan_status(self, scan_id: str) -> Dict[str, Any]:
           """Get scan status.
           
           Args:
               scan_id: Unique scan identifier
               
           Returns:
               Status information including progress and state
           """
           response = requests.get(
               f"{self.base_url}/scans/{scan_id}/status",
               headers=self.headers
           )
           response.raise_for_status()
           return response.json()
       
       def get_scan_details(self, scan_id: str) -> Dict[str, Any]:
           """Get complete scan details including results.
           
           Args:
               scan_id: Unique scan identifier
               
           Returns:
               Complete scan information and results
           """
           response = requests.get(
               f"{self.base_url}/scans/{scan_id}",
               headers=self.headers
           )
           response.raise_for_status()
           return response.json()
       
       def download_report(self, scan_id: str, report_type: str, filename: str):
           """Download a scan report.
           
           Args:
               scan_id: Unique scan identifier
               report_type: Type of report ('json', 'html', 'jsonl', 'hits')
               filename: Local filename to save the report
           """
           response = requests.get(
               f"{self.base_url}/scans/{scan_id}/reports/{report_type}",
               headers=self.headers
           )
           response.raise_for_status()
           
           with open(filename, 'wb') as f:
               f.write(response.content)
       
       def wait_for_completion(self, scan_id: str, timeout: int = 1800,
                             poll_interval: int = 30) -> Dict[str, Any]:
           """Wait for scan to complete.
           
           Args:
               scan_id: Unique scan identifier
               timeout: Maximum time to wait in seconds
               poll_interval: Time between status checks in seconds
               
           Returns:
               Complete scan details when finished
               
           Raises:
               TimeoutError: If scan doesn't complete within timeout
           """
           start_time = time.time()
           
           while time.time() - start_time < timeout:
               status = self.get_scan_status(scan_id)
               
               if status["status"] in ["completed", "failed", "cancelled"]:
                   return self.get_scan_details(scan_id)
               
               print(f"Status: {status['status']}")
               if 'progress' in status and status['progress']:
                   progress = status['progress']
                   percent = progress.get('progress_percent', 0)
                   print(f"Progress: {percent:.1f}%")
               
               time.sleep(poll_interval)
           
           raise TimeoutError(f"Scan {scan_id} did not complete within {timeout} seconds")
       
       def list_scans(self, page: int = 1, per_page: int = 20,
                     status: Optional[str] = None) -> Dict[str, Any]:
           """List scans with pagination.
           
           Args:
               page: Page number (1-based)
               per_page: Items per page
               status: Filter by status (optional)
               
           Returns:
               Paginated list of scans
           """
           params = {"page": page, "per_page": per_page}
           if status:
               params["status"] = status
           
           response = requests.get(
               f"{self.base_url}/scans",
               params=params,
               headers=self.headers
           )
           response.raise_for_status()
           return response.json()
       
       def list_generators(self) -> Dict[str, Any]:
           """List available model generators."""
           response = requests.get(
               f"{self.base_url}/generators",
               headers=self.headers
           )
           response.raise_for_status()
           return response.json()
       
       def list_probes(self) -> Dict[str, Any]:
           """List available security probes."""
           response = requests.get(
               f"{self.base_url}/probes",
               headers=self.headers
           )
           response.raise_for_status()
           return response.json()

Example Usage
-------------

Here's how to use the SDK to perform a complete security assessment:

.. code-block:: python

   # Initialize the API client
   api = GarakAPI("http://localhost:8080/api/v1", "your_api_key_here")

   # Configure a security scan
   scan_config = {
       "generator": "huggingface",
       "model_name": "gpt2",
       "probe_categories": ["toxicity", "hallucination"],
       "name": "GPT-2 Safety Assessment",
       "description": "Comprehensive safety testing of GPT-2",
       "parallel_attempts": 2
   }

   # Create and run the scan
   print("Creating security scan...")
   scan_id = api.create_scan(scan_config)
   print(f"Created scan: {scan_id}")

   # Wait for completion
   print("Waiting for scan to complete...")
   try:
       results = api.wait_for_completion(scan_id)
       print(f"Scan completed with status: {results['metadata']['status']}")
       
       # Download reports
       if results['metadata']['status'] == 'completed':
           print("Downloading reports...")
           api.download_report(scan_id, "json", f"scan_{scan_id}.json")
           api.download_report(scan_id, "html", f"scan_{scan_id}.html") 
           print("Reports downloaded successfully")
           
   except TimeoutError as e:
       print(f"Scan timed out: {e}")

Advanced Usage
--------------

Batch Scanning
~~~~~~~~~~~~~~

Scan multiple models in parallel:

.. code-block:: python

   import concurrent.futures
   
   def run_scan(model_config):
       scan_id = api.create_scan(model_config)
       return api.wait_for_completion(scan_id)
   
   models_to_test = [
       {"generator": "huggingface", "model_name": "gpt2"},
       {"generator": "huggingface", "model_name": "microsoft/DialoGPT-medium"}
   ]
   
   scan_configs = []
   for model in models_to_test:
       config = {
           **model,
           "probe_categories": ["toxicity"],
           "name": f"Toxicity Test - {model['model_name']}"
       }
       scan_configs.append(config)
   
   # Run scans in parallel
   with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
       results = list(executor.map(run_scan, scan_configs))

Error Handling
~~~~~~~~~~~~~~

Handle API errors gracefully:

.. code-block:: python

   import requests

   try:
       scan_id = api.create_scan(scan_config)
   except requests.exceptions.HTTPError as e:
       if e.response.status_code == 400:
           error_data = e.response.json()
           print(f"Invalid request: {error_data['message']}")
       elif e.response.status_code == 429:
           print("Rate limited. Please wait and try again.")
       else:
           print(f"API error: {e}")
   except requests.exceptions.ConnectionError:
       print("Could not connect to Garak API server")

Rate Limiting
~~~~~~~~~~~~~

Implement exponential backoff for rate limits:

.. code-block:: python

   import time
   import random

   def api_request_with_backoff(func, *args, max_retries=3, **kwargs):
       for attempt in range(max_retries):
           try:
               return func(*args, **kwargs)
           except requests.exceptions.HTTPError as e:
               if e.response.status_code == 429 and attempt < max_retries - 1:
                   # Exponential backoff with jitter
                   wait_time = (2 ** attempt) + random.uniform(0, 1)
                   print(f"Rate limited. Waiting {wait_time:.2f} seconds...")
                   time.sleep(wait_time)
                   continue
               raise

   # Usage
   scan_id = api_request_with_backoff(api.create_scan, scan_config)

Configuration Management
~~~~~~~~~~~~~~~~~~~~~~~

Manage API configuration with environment variables:

.. code-block:: python

   import os
   from typing import Optional
   
   class GarakConfig:
       def __init__(self):
           self.base_url = os.getenv('GARAK_API_URL', 'http://localhost:8080/api/v1')
           self.api_key = os.getenv('GARAK_API_KEY')
           
           if not self.api_key:
               raise ValueError("GARAK_API_KEY environment variable is required")
       
       def create_client(self) -> GarakAPI:
           return GarakAPI(self.base_url, self.api_key)
   
   # Usage
   config = GarakConfig()
   api = config.create_client()

Logging Integration
~~~~~~~~~~~~~~~~~~

Add comprehensive logging:

.. code-block:: python

   import logging

   # Configure logging
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(levelname)s - %(message)s'
   )

   class GarakAPI:
       def __init__(self, base_url: str, api_key: str):
           self.logger = logging.getLogger(__name__)
           # ... rest of initialization
       
       def create_scan(self, config: Dict[str, Any]) -> str:
           self.logger.info(f"Creating scan: {config.get('name', 'Unnamed')}")
           # ... existing code
           self.logger.info(f"Created scan with ID: {scan_id}")
           return scan_id

Best Practices
--------------

1. **Error Handling**: Always use try-catch blocks for API calls
2. **Rate Limiting**: Implement backoff strategies for 429 responses
3. **Timeouts**: Set appropriate timeouts for long-running scans
4. **Logging**: Log scan progress and errors for debugging
5. **Configuration**: Use environment variables for sensitive data
6. **Validation**: Validate scan configurations before submission
7. **Monitoring**: Check scan status regularly but not too frequently