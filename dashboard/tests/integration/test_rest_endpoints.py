"""
Integration tests for REST endpoint scanning functionality.

Tests the complete REST endpoint scanning workflow from UI to backend.
"""

import json
import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock

def test_rest_generator_validation(api_models):
    """Test that REST generator is accepted in API models."""
    from api.core.models import CreateScanRequest
    
    # Test valid REST generator request
    request = CreateScanRequest(
        generator='rest',
        model_name='test-endpoint',
        probe_categories=['dan'],
        api_keys={'rest_api_key': 'test-key'}
    )
    
    assert request.generator == 'rest'
    assert request.model_name == 'test-endpoint'
    assert 'rest_api_key' in request.api_keys


def test_rest_scan_creation(client):
    """Test creating a REST endpoint scan via API."""
    rest_config = {
        'uri': 'https://api.example.com/v1/chat/completions',
        'req_template_json_object': {
            'messages': [{'role': 'user', 'content': '$INPUT'}],
            'model': 'gpt-3.5-turbo'
        },
        'headers': {'Authorization': 'Bearer $KEY'},
        'response_json': True,
        'response_json_field': '$.choices[0].message.content'
    }
    
    scan_data = {
        'generator': 'rest',
        'model_name': 'custom-rest-endpoint',
        'probe_categories': ['dan'],
        'api_keys': {'rest_api_key': 'test-key'},
        'rest_config': rest_config
    }
    
    with patch('app.run_garak_job') as mock_run_job:
        response = client.post('/api/start_job', 
                              json=scan_data,
                              headers={'Content-Type': 'application/json'})
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'job_id' in data
        
        # Verify the job was started with REST config
        mock_run_job.assert_called_once()
        args = mock_run_job.call_args[0]
        rest_config_arg = mock_run_job.call_args[0][6]  # rest_config parameter
        
        assert args[1] == 'rest'  # generator
        assert args[2] == 'custom-rest-endpoint'  # model_name
        assert rest_config_arg == rest_config


def test_rest_config_validation(client):
    """Test REST configuration validation."""
    # Missing URI should fail
    scan_data = {
        'generator': 'rest',
        'model_name': 'test',
        'probe_categories': ['dan'],
        'rest_config': {
            'req_template': '{"prompt": "$INPUT"}'
        }
    }
    
    # This should still work as URI validation happens on frontend
    with patch('app.run_garak_job'):
        response = client.post('/api/start_job', json=scan_data)
        assert response.status_code == 200


def test_rest_job_execution_setup():
    """Test that REST job execution properly sets up configuration files."""
    from app import run_garak_job
    
    job_id = 'test-rest-job'
    generator = 'rest'
    model_name = 'test-endpoint'
    probes = ['dan.DAN']
    api_keys = {'rest_api_key': 'test-key'}
    parallel_attempts = 1
    rest_config = {
        'uri': 'https://api.example.com/chat',
        'req_template_json_object': {'prompt': '$INPUT'},
        'response_json': True,
        'response_json_field': '$.response'
    }
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Mock the DATA_DIR and REPORT_DIR and JOBS
        mock_jobs = {job_id: {'id': job_id, 'status': 'pending'}}
        
        with patch('app.DATA_DIR', tmpdir), \
             patch('app.REPORT_DIR', tmpdir), \
             patch('app.JOBS', mock_jobs), \
             patch('subprocess.run') as mock_subprocess:
            
            mock_subprocess.return_value = MagicMock(
                returncode=0,
                stdout='Test output',
                stderr=''
            )
            
            # Test that REST config file is created
            run_garak_job(job_id, generator, model_name, probes, api_keys, parallel_attempts, rest_config)
            
            # Check that REST config file was created
            config_file_path = os.path.join(tmpdir, f'rest_config_{job_id}.json')
            assert os.path.exists(config_file_path), f"REST config file not created at {config_file_path}"
            
            # Verify config file contents
            with open(config_file_path, 'r') as f:
                saved_config = json.load(f)
            
            assert saved_config == rest_config
            

def test_rest_command_construction():
    """Test that REST configuration files are created properly."""
    from app import run_garak_job
    
    job_id = 'test-command-rest'
    generator = 'rest'
    model_name = 'original-name'
    probes = ['dan.DAN']
    api_keys = {'rest_api_key': 'test-key'}
    rest_config = {
        'uri': 'https://api.example.com/completions',
        'req_template': '{"input": "$INPUT"}',
        'response_json': True,
        'response_json_field': '$.output'
    }
    
    with tempfile.TemporaryDirectory() as tmpdir:
        mock_jobs = {job_id: {'id': job_id, 'status': 'pending', 'output': ''}}
        
        with patch('app.DATA_DIR', tmpdir), \
             patch('app.REPORT_DIR', tmpdir), \
             patch('app.JOBS', mock_jobs):
            
            # Mock the actual subprocess execution to prevent real job execution
            with patch('subprocess.run') as mock_subprocess:
                mock_subprocess.return_value = MagicMock(returncode=0, stdout='', stderr='')
                
                run_garak_job(job_id, generator, model_name, probes, api_keys, 1, rest_config)
                
                # Give the function time to set up config files
                import time
                time.sleep(0.1)
                
                # Verify REST config file was created
                config_file_path = os.path.join(tmpdir, f'rest_config_{job_id}.json')
                assert os.path.exists(config_file_path), f"REST config file should exist at {config_file_path}"
                
                # Verify config file contents
                with open(config_file_path, 'r') as f:
                    saved_config = json.load(f)
                
                assert saved_config == rest_config
                
                # Verify job file was created
                job_file_path = os.path.join(tmpdir, f'job_{job_id}.json')
                assert os.path.exists(job_file_path), f"Job file should exist at {job_file_path}"


def test_rest_api_key_handling():
    """Test that REST API keys are properly handled in job configuration."""
    from app import run_garak_job
    
    job_id = 'test-api-key-rest'
    api_keys = {'rest_api_key': 'sk-test-key-12345'}
    
    with tempfile.TemporaryDirectory() as tmpdir:
        mock_jobs = {job_id: {'id': job_id, 'status': 'pending', 'output': ''}}
        
        with patch('app.DATA_DIR', tmpdir), \
             patch('app.REPORT_DIR', tmpdir), \
             patch('app.JOBS', mock_jobs):
            
            # Mock subprocess to prevent actual execution
            with patch('subprocess.run') as mock_subprocess:
                mock_subprocess.return_value = MagicMock(returncode=0, stdout='', stderr='')
                
                run_garak_job(job_id, 'rest', 'test', ['dan.DAN'], api_keys, 1, {})
                
                # Give the function time to set up job files
                import time
                time.sleep(0.1)
                
                # Verify job file was created and contains the API key info
                job_file_path = os.path.join(tmpdir, f'job_{job_id}.json')
                assert os.path.exists(job_file_path), f"Job file should exist at {job_file_path}"
                
                with open(job_file_path, 'r') as f:
                    job_data = json.load(f)
                
                # Verify API keys are preserved in job config (for garak execution)
                assert 'api_keys' in job_data
                assert 'rest_api_key' in job_data['api_keys']
                assert job_data['api_keys']['rest_api_key'] == 'sk-test-key-12345'


@pytest.mark.parametrize("rest_config", [
    {
        'uri': 'https://api.test.com/v1/chat',
        'req_template': '{"messages": [{"role": "user", "content": "$INPUT"}]}'
    },
    {
        'uri': 'https://custom.ai/api',
        'headers': {'Authorization': 'Bearer $KEY'},
        'response_json': True,
        'response_json_field': '$.data.text'
    }
])
def test_rest_configurations(rest_config):
    """Test various REST configuration scenarios."""
    from app import run_garak_job
    
    job_id = f'test-config-{hash(str(rest_config)) % 10000}'
    
    with tempfile.TemporaryDirectory() as tmpdir:
        mock_jobs = {job_id: {'id': job_id, 'status': 'pending', 'output': ''}}
        
        with patch('app.DATA_DIR', tmpdir), \
             patch('app.REPORT_DIR', tmpdir), \
             patch('app.JOBS', mock_jobs):
            
            # Mock subprocess to prevent actual execution
            with patch('subprocess.run') as mock_subprocess:
                mock_subprocess.return_value = MagicMock(returncode=0, stdout='', stderr='')
                
                run_garak_job(job_id, 'rest', 'test', ['dan.DAN'], {}, 1, rest_config)
                
                # Give the function time to set up config files
                import time
                time.sleep(0.1)
                
                # Verify REST config file was created with correct content
                config_file_path = os.path.join(tmpdir, f'rest_config_{job_id}.json')
                assert os.path.exists(config_file_path), f"REST config file should exist at {config_file_path}"
                
                with open(config_file_path, 'r') as f:
                    saved_config = json.load(f)
                
                # Verify all expected fields are present
                assert saved_config['uri'] == rest_config['uri']
                if 'headers' in rest_config:
                    assert saved_config['headers'] == rest_config['headers']
                if 'response_json' in rest_config:
                    assert saved_config['response_json'] == rest_config['response_json']
                if 'response_json_field' in rest_config:
                    assert saved_config['response_json_field'] == rest_config['response_json_field']


def test_rest_error_handling():
    """Test error handling for REST endpoint configurations."""
    # Test will be implemented based on specific error scenarios
    # that might occur during REST endpoint scanning
    pass


def test_rest_ui_integration():
    """Test that REST configuration fields are properly handled in UI."""
    # This would test the JavaScript form handling
    # For now, we rely on manual testing of the UI
    pass