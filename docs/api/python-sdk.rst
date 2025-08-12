Python SDK
==========

Simple Python client for the Garak API.

Basic Usage
-----------

.. code-block:: python

   import requests

   class GarakAPI:
       def __init__(self, base_url: str, api_key: str):
           self.base_url = base_url.rstrip('/')
           self.headers = {
               "X-API-Key": api_key,
               "Content-Type": "application/json"
           }
       
       def create_scan(self, config):
           response = requests.post(f"{self.base_url}/scans", json=config, headers=self.headers)
           response.raise_for_status()
           return response.json()["scan_id"]
       
       def get_scan_status(self, scan_id):
           response = requests.get(f"{self.base_url}/scans/{scan_id}/status", headers=self.headers)
           response.raise_for_status()
           return response.json()
       
       def download_report(self, scan_id, report_type, filename):
           response = requests.get(f"{self.base_url}/scans/{scan_id}/reports/{report_type}", headers=self.headers)
           response.raise_for_status()
           with open(filename, 'wb') as f:
               f.write(response.content)

Example
-------

.. code-block:: python

   # Initialize client
   api = GarakAPI("https://your-api-domain.com/api/v1", "your_api_key_here")

   # Create scan
   scan_config = {
       "generator": "huggingface",
       "model_name": "gpt2"
   }
   scan_id = api.create_scan(scan_config)

   # Check status
   status = api.get_scan_status(scan_id)
   print(f"Status: {status['status']}")

   # Download report when completed
   if status['status'] == 'completed':
       api.download_report(scan_id, "json", "report.json")