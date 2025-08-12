Usage Examples
==============

This section provides practical examples for common API use cases.

Basic Scan Creation
-------------------

Example 1: Simple Toxicity Test
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Test a model for toxic content generation:

.. code-block:: bash

   curl -X POST https://your-api-domain.com/api/v1/scans \
        -H "X-API-Key: your_api_key" \
        -H "Content-Type: application/json" \
        -d '{
          "generator": "huggingface",
          "model_name": "gpt2",
          "probe_categories": ["realtoxicityprompts"],
          "name": "GPT-2 Toxicity Test",
          "description": "Testing GPT-2 for toxic content generation"
        }'

Example 2: Comprehensive Security Assessment  
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run multiple probe categories for thorough testing:

.. code-block:: bash

   curl -X POST https://your-api-domain.com/api/v1/scans \
        -H "X-API-Key: your_api_key" \
        -H "Content-Type: application/json" \
        -d '{
          "generator": "openai", 
          "model_name": "gpt-3.5-turbo",
          "probe_categories": ["dan", "promptinject", "realtoxicityprompts"],
          "api_keys": {
            "openai_api_key": "sk-your-openai-key"
          },
          "name": "GPT-3.5 Comprehensive Security Audit",
          "description": "Full security assessment including DAN, injection, privacy and toxicity tests",
          "parallel_attempts": 3
        }'

Example 3: Specific Probe Testing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Target specific probes instead of categories:

.. code-block:: bash

   curl -X POST https://your-api-domain.com/api/v1/scans \
        -H "X-API-Key: your_api_key" \
        -H "Content-Type: application/json" \
        -d '{
          "generator": "anthropic",
          "model_name": "claude-3-sonnet-20240229", 
          "probes": [
            "dan.Dan_11_0",
            "promptinject.HijackKillHumans",
            "leakreplay.GuardianCloze"
          ],
          "api_keys": {
            "anthropic_api_key": "your-anthropic-key"
          },
          "name": "Claude Targeted Security Test"
        }'

Monitoring and Management
------------------------

Example 4: Monitor Scan Progress
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Poll scan status and download results:

.. code-block:: bash

   # Check status
   SCAN_ID="your-scan-id"
   curl -H "X-API-Key: your_api_key" \
        "https://your-api-domain.com/api/v1/scans/$SCAN_ID/status"

   # Get detailed progress
   curl -H "X-API-Key: your_api_key" \
        "https://your-api-domain.com/api/v1/scans/$SCAN_ID/progress"

   # Download results when complete
   curl -H "X-API-Key: your_api_key" \
        "https://your-api-domain.com/api/v1/scans/$SCAN_ID/reports/json" \
        -o results.json

Example 5: List and Filter Scans
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # List all scans
   curl -H "X-API-Key: your_api_key" \
        "http://localhost:8080/api/v1/scans"

   # Filter by status  
   curl -H "X-API-Key: your_api_key" \
        "http://localhost:8080/api/v1/scans?status=completed&per_page=10"

   # Get specific scan details
   curl -H "X-API-Key: your_api_key" \
        "https://your-api-domain.com/api/v1/scans/$SCAN_ID"

Python Examples
---------------

Example 6: Complete Python Workflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import requests
   import time
   import json

   # Configuration
   API_KEY = "your_api_key_here"
   BASE_URL = "http://localhost:8080/api/v1"
   HEADERS = {
       "X-API-Key": API_KEY,
       "Content-Type": "application/json"
   }

   def create_scan(config):
       response = requests.post(f"{BASE_URL}/scans", json=config, headers=HEADERS)
       response.raise_for_status()
       return response.json()["scan_id"]

   def wait_for_completion(scan_id, timeout=1800):
       start_time = time.time()
       while time.time() - start_time < timeout:
           response = requests.get(f"{BASE_URL}/scans/{scan_id}/status", headers=HEADERS)
           status = response.json()["status"]
           
           if status in ["completed", "failed", "cancelled"]:
               return status
           
           print(f"Status: {status}")
           time.sleep(30)
       
       raise TimeoutError("Scan did not complete")

   def download_report(scan_id, report_type="json"):
       response = requests.get(f"{BASE_URL}/scans/{scan_id}/reports/{report_type}", headers=HEADERS)
       response.raise_for_status()
       return response.content

   # Main workflow
   scan_config = {
       "generator": "huggingface",
       "model_name": "gpt2", 
       "probe_categories": ["hallucination", "toxicity"],
       "name": "Automated Safety Check",
       "parallel_attempts": 2
   }

   print("Creating scan...")
   scan_id = create_scan(scan_config)
   print(f"Scan ID: {scan_id}")

   print("Waiting for completion...")
   status = wait_for_completion(scan_id)
   print(f"Final status: {status}")

   if status == "completed":
       print("Downloading reports...")
       json_report = download_report(scan_id, "json")
       html_report = download_report(scan_id, "html")
       
       with open(f"scan_{scan_id}.json", "wb") as f:
           f.write(json_report)
       with open(f"scan_{scan_id}.html", "wb") as f:
           f.write(html_report)
       
       print("Reports saved successfully!")

Example 7: Batch Testing Multiple Models
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import concurrent.futures

   models_to_test = [
       {"generator": "huggingface", "model_name": "gpt2"},
       {"generator": "huggingface", "model_name": "microsoft/DialoGPT-medium"},
       {"generator": "ollama", "model_name": "llama2"}
   ]

   def test_model(model):
       config = {
           **model,
           "probe_categories": ["realtoxicityprompts"],
           "name": f"Toxicity Test - {model['model_name']}"
       }
       
       scan_id = create_scan(config)
       status = wait_for_completion(scan_id)
       
       return {
           "model": model["model_name"],
           "scan_id": scan_id,
           "status": status
       }

   # Run tests in parallel
   with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
       results = list(executor.map(test_model, models_to_test))

   for result in results:
       print(f"Model {result['model']}: {result['status']}")

Discovery Examples
------------------

Example 8: Explore Available Options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # List all generators
   curl -H "X-API-Key: your_api_key" \
        "http://localhost:8080/api/v1/generators"

   # Get specific generator details
   curl -H "X-API-Key: your_api_key" \
        "http://localhost:8080/api/v1/generators/openai"

   # List all probes
   curl -H "X-API-Key: your_api_key" \
        "http://localhost:8080/api/v1/probes"

   # Get probes in specific category
   curl -H "X-API-Key: your_api_key" \
        "http://localhost:8080/api/v1/probes/dan"

Example 9: Dynamic Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Discover available options
   def get_available_options():
       generators = requests.get(f"{BASE_URL}/generators", headers=HEADERS).json()
       probes = requests.get(f"{BASE_URL}/probes", headers=HEADERS).json()
       return generators, probes

   generators, probes = get_available_options()

   # Find generators that don't require API keys
   free_generators = [
       g for g in generators["generators"] 
       if not g["requires_api_key"]
   ]

   # Get all probe categories
   categories = [cat["name"] for cat in probes["categories"]]

   print(f"Free generators: {[g['name'] for g in free_generators]}")
   print(f"Available categories: {categories}")

Error Handling Examples
-----------------------

Example 10: Robust Error Handling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import requests
   from requests.exceptions import HTTPError, ConnectionError, Timeout

   def safe_api_call(func, *args, **kwargs):
       try:
           return func(*args, **kwargs)
       except HTTPError as e:
           if e.response.status_code == 400:
               error_data = e.response.json()
               print(f"Bad request: {error_data['message']}")
               return None
           elif e.response.status_code == 401:
               print("Authentication failed - check your API key")
               return None
           elif e.response.status_code == 429:
               print("Rate limited - waiting before retry...")
               time.sleep(60)
               return func(*args, **kwargs)  # Retry once
           else:
               print(f"HTTP error: {e}")
               return None
       except ConnectionError:
           print("Could not connect to API server")
           return None
       except Timeout:
           print("Request timed out")
           return None

   # Usage
   def create_scan_safely(config):
       response = safe_api_call(
           requests.post,
           f"{BASE_URL}/scans",
           json=config,
           headers=HEADERS
       )
       if response:
           return response.json()["scan_id"]
       return None

Advanced Examples
-----------------

Example 11: Custom REST Endpoint Testing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   curl -X POST https://your-api-domain.com/api/v1/scans \
        -H "X-API-Key: your_api_key" \
        -H "Content-Type: application/json" \
        -d '{
          "generator": "rest",
          "model_name": "custom-model",
          "probe_categories": ["dan"],
          "rest_config": {
            "endpoint": "https://api.example.com/v1/chat/completions",
            "method": "POST",
            "headers": {
              "Authorization": "Bearer your-token",
              "Content-Type": "application/json"
            },
            "request_format": "openai",
            "response_format": "openai"
          },
          "name": "Custom API Security Test"
        }'

Example 12: Report Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import json

   def analyze_scan_results(scan_id):
       # Download JSON report
       response = requests.get(f"{BASE_URL}/scans/{scan_id}/reports/json", headers=HEADERS)
       report = response.json()
       
       # Extract key metrics
       total_attempts = len(report.get("attempts", []))
       failed_attempts = sum(1 for attempt in report.get("attempts", []) if attempt.get("status") == "failed")
       
       # Count by probe category
       category_results = {}
       for attempt in report.get("attempts", []):
           category = attempt.get("probe", "").split(".")[0]
           if category not in category_results:
               category_results[category] = {"total": 0, "failed": 0}
           category_results[category]["total"] += 1
           if attempt.get("status") == "failed":
               category_results[category]["failed"] += 1
       
       # Calculate failure rates
       for category, stats in category_results.items():
           stats["failure_rate"] = (stats["failed"] / stats["total"]) * 100
       
       return {
           "total_attempts": total_attempts,
           "failed_attempts": failed_attempts,
           "overall_failure_rate": (failed_attempts / total_attempts) * 100 if total_attempts > 0 else 0,
           "category_breakdown": category_results
       }

   # Usage
   analysis = analyze_scan_results("your-scan-id")
   print(f"Overall failure rate: {analysis['overall_failure_rate']:.1f}%")
   
   for category, stats in analysis["category_breakdown"].items():
       print(f"{category}: {stats['failure_rate']:.1f}% failure rate ({stats['failed']}/{stats['total']})")

Complete Integration Example
---------------------------

Example 13: CI/CD Pipeline Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   #!/usr/bin/env python3
   """
   Garak Security Testing for CI/CD Pipeline
   """
   
   import sys
   import os
   import requests
   import time
   import json
   from typing import Dict, List, Optional

   class GarakSecurityTest:
       def __init__(self, api_key: str, base_url: str = "http://localhost:8080/api/v1"):
           self.api_key = api_key
           self.base_url = base_url
           self.headers = {
               "X-API-Key": api_key,
               "Content-Type": "application/json"
           }
       
       def run_security_gate(self, model_config: Dict, failure_threshold: float = 10.0) -> bool:
           """
           Run security gate check for CI/CD pipeline.
           Returns False if failure rate exceeds threshold.
           """
           print(f"🔍 Running security gate for {model_config['model_name']}...")
           
           # Create scan
           scan_config = {
               **model_config,
               "probe_categories": ["dan", "security", "toxicity"],
               "name": f"CI/CD Security Gate - {model_config['model_name']}",
               "parallel_attempts": 1  # Keep CI fast
           }
           
           try:
               response = requests.post(f"{self.base_url}/scans", json=scan_config, headers=self.headers)
               response.raise_for_status()
               scan_id = response.json()["scan_id"]
               print(f"📋 Created scan: {scan_id}")
               
               # Wait for completion
               print("⏳ Waiting for scan completion...")
               status = self._wait_for_completion(scan_id, timeout=600)  # 10 min max for CI
               
               if status != "completed":
                   print(f"❌ Scan failed with status: {status}")
                   return False
               
               # Analyze results
               analysis = self._analyze_results(scan_id)
               failure_rate = analysis["overall_failure_rate"]
               
               print(f"📊 Security Analysis Results:")
               print(f"   Overall failure rate: {failure_rate:.1f}%")
               print(f"   Threshold: {failure_threshold}%")
               
               if failure_rate > failure_threshold:
                   print(f"❌ SECURITY GATE FAILED: Failure rate {failure_rate:.1f}% exceeds threshold {failure_threshold}%")
                   self._print_detailed_results(analysis)
                   return False
               else:
                   print(f"✅ SECURITY GATE PASSED: Failure rate {failure_rate:.1f}% within acceptable threshold")
                   return True
                   
           except Exception as e:
               print(f"❌ Security gate error: {e}")
               return False
       
       def _wait_for_completion(self, scan_id: str, timeout: int = 600) -> str:
           start_time = time.time()
           while time.time() - start_time < timeout:
               response = requests.get(f"{self.base_url}/scans/{scan_id}/status", headers=self.headers)
               status_data = response.json()
               status = status_data["status"]
               
               if status in ["completed", "failed", "cancelled"]:
                   return status
               
               time.sleep(10)  # Check every 10 seconds for CI
           
           return "timeout"
       
       def _analyze_results(self, scan_id: str) -> Dict:
           response = requests.get(f"{self.base_url}/scans/{scan_id}/reports/json", headers=self.headers)
           report = response.json()
           
           attempts = report.get("attempts", [])
           total = len(attempts)
           failed = sum(1 for attempt in attempts if attempt.get("status") == "failed")
           
           return {
               "total_attempts": total,
               "failed_attempts": failed,
               "overall_failure_rate": (failed / total) * 100 if total > 0 else 0
           }
       
       def _print_detailed_results(self, analysis: Dict):
           print("📋 Detailed Results:")
           print(f"   Total attempts: {analysis['total_attempts']}")
           print(f"   Failed attempts: {analysis['failed_attempts']}")
           print("   Consider reviewing and improving model safety measures")

   def main():
       api_key = os.getenv("GARAK_API_KEY")
       if not api_key:
           print("❌ GARAK_API_KEY environment variable required")
           sys.exit(1)
       
       model_config = {
           "generator": "huggingface",
           "model_name": "gpt2"
       }
       
       security_test = GarakSecurityTest(api_key)
       
       # Run security gate with 5% failure threshold
       passed = security_test.run_security_gate(model_config, failure_threshold=5.0)
       
       if passed:
           print("🎉 Model passed security gate - deployment can proceed")
           sys.exit(0)
       else:
           print("🛑 Model failed security gate - deployment blocked")
           sys.exit(1)

   if __name__ == "__main__":
       main()

This script can be integrated into your CI/CD pipeline:

.. code-block:: yaml

   # .github/workflows/security-gate.yml
   name: Security Gate
   on: [push, pull_request]
   
   jobs:
     security-test:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v2
         - name: Run Garak Security Gate
           env:
             GARAK_API_KEY: ${{ secrets.GARAK_API_KEY }}
           run: python security_gate.py