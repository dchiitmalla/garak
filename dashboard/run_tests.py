#!/usr/bin/env python3
"""
Test runner script for Garak Dashboard.

This script provides various test running options for the dashboard test suite.
"""

import subprocess
import sys
import argparse
import os


def run_command(cmd, description):
    """Run a command and return the result."""
    print(f"\n🚀 {description}")
    print(f"Running: {' '.join(cmd)}")
    print("-" * 60)
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Run Garak Dashboard tests")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--auth", action="store_true", help="Run authentication tests only")
    parser.add_argument("--models", action="store_true", help="Run model tests only")
    parser.add_argument("--api", action="store_true", help="Run API endpoint tests only")
    parser.add_argument("--coverage", action="store_true", help="Run tests with coverage")
    parser.add_argument("--html", action="store_true", help="Generate HTML test report")
    parser.add_argument("--parallel", action="store_true", help="Run tests in parallel")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--fast", action="store_true", help="Run only fast tests")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    
    args = parser.parse_args()
    
    # Set up environment
    os.environ['DISABLE_AUTH'] = 'true'
    os.environ['FLASK_ENV'] = 'testing'
    
    # Base pytest command
    base_cmd = [sys.executable, "-m", "pytest"]
    
    # Add verbosity
    if args.verbose:
        base_cmd.extend(["-v", "-s"])
    
    # Add parallel execution if requested
    if args.parallel:
        base_cmd.extend(["-n", "auto"])
    
    # Add coverage if requested
    if args.coverage:
        base_cmd.extend(["--cov=api", "--cov-report=term-missing"])
        if args.html:
            base_cmd.extend(["--cov-report=html"])
    
    # Add HTML report if requested
    if args.html and not args.coverage:
        base_cmd.extend(["--html=test_report.html", "--self-contained-html"])
    
    success = True
    
    if args.unit:
        cmd = base_cmd + ["tests/unit/", "-m", "unit"]
        success &= run_command(cmd, "Unit Tests")
    
    elif args.integration:
        cmd = base_cmd + ["tests/integration/", "-m", "integration"]
        success &= run_command(cmd, "Integration Tests")
    
    elif args.auth:
        cmd = base_cmd + ["tests/", "-m", "auth"]
        success &= run_command(cmd, "Authentication Tests")
    
    elif args.models:
        cmd = base_cmd + ["tests/", "-m", "models"] 
        success &= run_command(cmd, "Model Tests")
    
    elif args.api:
        cmd = base_cmd + ["tests/", "-m", "api"]
        success &= run_command(cmd, "API Endpoint Tests")
    
    elif args.fast:
        cmd = base_cmd + ["tests/", "-m", "not slow"]
        success &= run_command(cmd, "Fast Tests")
    
    elif args.all or not any([args.unit, args.integration, args.auth, args.models, args.api, args.fast]):
        # Run all tests by default
        cmd = base_cmd + ["tests/"]
        success &= run_command(cmd, "All Tests")
    
    # Summary
    print("\n" + "=" * 60)
    if success:
        print("🎉 All requested tests completed successfully!")
    else:
        print("⚠️  Some tests failed. Check the output above.")
    print("=" * 60)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())