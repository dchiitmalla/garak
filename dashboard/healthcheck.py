#!/usr/bin/env python3
"""
Health check script for Garak Dashboard Docker container.
"""

import sys
import requests
import os

def health_check():
    """Check if the application is healthy."""
    try:
        port = os.environ.get('PORT', '8080')
        url = f"http://localhost:{port}/api/v1/health"
        
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'healthy':
                print("Health check passed")
                return 0
        
        print(f"Health check failed: status={response.status_code}")
        return 1
        
    except Exception as e:
        print(f"Health check failed with exception: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(health_check())