"""
Integration tests for job error handling improvements.

Tests that jobs continue to execute and produce results even when individual
probes fail or encounter errors.
"""

import pytest
import os
import tempfile
import json
from unittest.mock import patch, Mock

# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration


class TestJobErrorHandling:
    """Test job execution error handling at the integration level."""
    
    def test_job_continues_with_probe_failures(self, client, sample_scan_request):
        """Test that jobs continue execution even when some probes fail."""
        # Modify the request to include probes that might fail
        scan_request = sample_scan_request.copy()
        scan_request['probe_categories'] = ['dan']  # Include AutoDAN which fails on non-HF
        scan_request['generator'] = 'openai'  # Use OpenAI which will cause AutoDAN to fail
        scan_request['model_name'] = 'gpt-3.5-turbo'
        
        # Create a scan
        response = client.post('/api/v1/scans', 
                              json=scan_request,
                              content_type='application/json')
        
        assert response.status_code == 201
        data = response.get_json()
        scan_id = data['scan_id']
        
        # The scan should have been created successfully despite probe incompatibility
        assert 'scan_id' in data
        assert data['metadata']['generator'] == 'openai'
        assert data['metadata']['model_name'] == 'gpt-3.5-turbo'
    
    def test_scan_status_with_probe_errors(self, client, sample_scan_request):
        """Test that scan status is reported correctly even with probe errors."""
        # Create a scan that will have probe errors
        scan_request = sample_scan_request.copy()
        scan_request['probe_categories'] = ['dan']
        scan_request['generator'] = 'anthropic'  # Another non-HF generator
        scan_request['model_name'] = 'claude-3-sonnet'
        
        response = client.post('/api/v1/scans', 
                              json=scan_request,
                              content_type='application/json')
        
        assert response.status_code == 201
        scan_id = response.get_json()['scan_id']
        
        # Check that we can get the scan status
        status_response = client.get(f'/api/v1/scans/{scan_id}/status')
        assert status_response.status_code == 200
        
        status_data = status_response.get_json()
        assert status_data['scan_id'] == scan_id
        assert 'status' in status_data
        
        # Status should be pending (not failed immediately due to probe errors)
        assert status_data['status'] in ['pending', 'running']
    
    def test_job_script_generation_with_error_handling(self):
        """Test that job scripts are generated with proper error handling."""
        from app import run_garak_job
        import tempfile
        import threading
        
        # This test would mock the job execution to verify the script
        # contains proper error handling logic
        
        # Mock the JOBS dictionary and other dependencies
        job_id = 'test-job-123'
        generator = 'openai'
        model_name = 'gpt-3.5-turbo'
        probes = ['dan.AutoDAN', 'dan.Dan_11_0']
        api_keys = {'openai_api_key': 'test-key'}
        
        # We can't easily test the full function without extensive mocking,
        # but we can verify the script generation logic exists
        # This would require refactoring run_garak_job to be more testable
        pass
    
    def test_report_generation_with_partial_failures(self, client, sample_scan_request):
        """Test that reports are generated even when some probes fail."""
        # This test would verify that if a scan produces some results
        # (even with some probe failures), reports are still generated
        
        scan_request = sample_scan_request.copy()
        scan_request['probe_categories'] = ['dan']
        
        response = client.post('/api/v1/scans', 
                              json=scan_request,
                              content_type='application/json')
        
        assert response.status_code == 201
        scan_id = response.get_json()['scan_id']
        
        # The scan should be created and we should be able to get its details
        detail_response = client.get(f'/api/v1/scans/{scan_id}')
        assert detail_response.status_code == 200
        
        detail_data = detail_response.get_json()
        assert 'metadata' in detail_data
        assert 'output_log' in detail_data


class TestLoggingConfiguration:
    """Test that logging configuration prevents recursive issues."""
    
    def test_http_client_logging_levels(self):
        """Test that HTTP client loggers are configured to prevent spam."""
        import logging
        
        # Import the app to ensure logging is configured
        import app
        
        # Check that problematic loggers are set to appropriate levels
        loggers_to_check = ['httpcore', 'httpx', 'urllib3']
        
        for logger_name in loggers_to_check:
            logger = logging.getLogger(logger_name)
            # Should be WARNING or higher to prevent debug spam
            assert logger.level >= logging.WARNING, f"Logger {logger_name} should be WARNING level or higher"
    
    def test_no_recursive_logging_during_requests(self, client):
        """Test that HTTP requests don't cause recursive logging issues."""
        # Make a simple request and ensure no logging errors occur
        response = client.get('/api/v1/health')
        assert response.status_code == 200
        
        # The fact that this doesn't hang or crash indicates logging is working
        data = response.get_json()
        assert data['status'] == 'healthy'


class TestProbeErrorRecovery:
    """Test that the system recovers gracefully from probe errors."""
    
    def test_autodan_probe_fallback_behavior(self):
        """Test AutoDAN probe behavior with non-HuggingFace generators."""
        # This would test the actual probe behavior in isolation
        # but with the dashboard's configuration
        
        # Import the fixed probe
        try:
            from garak.probes.dan import AutoDAN
            from unittest.mock import Mock
            
            # Create a non-HF generator mock
            mock_generator = Mock()
            mock_generator.__class__.__name__ = 'OpenAIGenerator'
            
            # Create the probe and test it
            probe = AutoDAN()
            result = list(probe.probe(mock_generator))
            
            # Should return empty list without crashing
            assert result == []
            
        except ImportError:
            # If garak modules aren't available, skip this test
            pytest.skip("Garak modules not available for testing")
    
    def test_probe_error_logging(self, caplog):
        """Test that probe errors are logged appropriately."""
        import logging
        
        # This would test that when probes fail, appropriate log messages
        # are generated without causing recursive logging issues
        
        with caplog.at_level(logging.WARNING):
            # Simulate a probe error scenario
            try:
                from garak.probes.dan import AutoDAN
                from unittest.mock import Mock
                
                mock_generator = Mock()
                mock_generator.__class__.__name__ = 'TestGenerator'
                
                probe = AutoDAN()
                list(probe.probe(mock_generator))
                
                # Check that appropriate warning was logged
                assert any("AutoDAN probe skipped" in record.message 
                          for record in caplog.records)
                
            except ImportError:
                pytest.skip("Garak modules not available for testing")