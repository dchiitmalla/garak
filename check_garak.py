#!/usr/bin/env python3
import sys
import os

print("Python Path:")
print(sys.path)
print("\nPython Version:")
print(sys.version)
print("\nChecking for garak package:")
try:
    import garak
    print("Garak package found and imported successfully")
    print("Garak path:", garak.__file__)
    
    # Check for specific modules
    try:
        from garak.evaluators.base import DetectOnly
        print("Successfully imported DetectOnly from garak.evaluators.base")
    except ImportError as e:
        print("Error importing DetectOnly:", e)
        
except ImportError as e:
    print("Error importing garak:", e)

print("\nEnvironment Variables:")
for key, value in os.environ.items():
    if key.startswith("PYTHON") or "PATH" in key:
        print(f"{key}: {value}")

print("\nListing /app directory:")
try:
    print(os.listdir("/app"))
except Exception as e:
    print(f"Error listing /app: {str(e)}")
