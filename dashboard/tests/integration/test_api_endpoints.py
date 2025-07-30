"""
Integration tests for API endpoints.
"""

import pytest
import json


class TestHealthEndpoints:
    """Test health and info endpoints."""
    
    def test_health_endpoint(self, client):
        """Test /api/v1/health endpoint."""
        response = client.get('/api/v1/health')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['status'] == 'healthy'
        assert 'services' in data
        assert 'timestamp' in data
    
    def test_info_endpoint(self, client):
        """Test /api/v1/info endpoint."""
        response = client.get('/api/v1/info')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'version' in data  # Required for compatibility
        assert 'api_version' in data
        assert 'capabilities' in data
        assert data['service'] == 'Garak LLM Security Scanner'


class TestGeneratorEndpoints:
    """Test generator metadata endpoints."""
    
    def test_list_generators(self, client):
        """Test GET /api/v1/generators."""
        response = client.get('/api/v1/generators')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'generators' in data
        assert 'total' in data
        assert data['total'] > 0
        
        # Verify generator structure
        for gen in data['generators']:
            assert 'name' in gen
            assert 'display_name' in gen
            assert 'requires_api_key' in gen
            assert 'supported_models' in gen
            assert isinstance(gen['supported_models'], list)
    
    def test_get_specific_generator(self, client):
        """Test GET /api/v1/generators/{name}."""
        response = client.get('/api/v1/generators/openai')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['name'] == 'openai'
        assert data['display_name'] == 'OpenAI'
        assert data['requires_api_key'] is True
        assert len(data['supported_models']) > 0
        assert 'gpt-4' in data['supported_models']
    
    def test_get_huggingface_generator(self, client):
        """Test GET /api/v1/generators/huggingface."""
        response = client.get('/api/v1/generators/huggingface')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['name'] == 'huggingface'
        assert data['display_name'] == 'Hugging Face'
        assert data['requires_api_key'] is False
    
    def test_get_nonexistent_generator(self, client):
        """Test GET /api/v1/generators/{nonexistent}."""
        response = client.get('/api/v1/generators/nonexistent')
        assert response.status_code == 404
        
        data = response.get_json()
        assert 'error' in data
        assert 'message' in data


class TestProbeEndpoints:
    """Test probe metadata endpoints."""
    
    def test_list_probes(self, client):
        """Test GET /api/v1/probes."""
        response = client.get('/api/v1/probes')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'categories' in data
        assert len(data['categories']) > 0
        
        # Find DAN category for testing
        dan_category = next((cat for cat in data['categories'] if cat['name'] == 'dan'), None)
        assert dan_category is not None
        assert dan_category['display_name'] == 'DAN (Do Anything Now)'
        assert len(dan_category['probes']) > 0
        
        # Verify probe structure
        first_probe = dan_category['probes'][0]
        assert 'name' in first_probe
        assert 'display_name' in first_probe
        assert 'category' in first_probe
        assert first_probe['category'] == 'dan'
    
    def test_probe_categories_structure(self, client):
        """Test that probe categories have proper structure."""
        response = client.get('/api/v1/probes')
        assert response.status_code == 200
        
        data = response.get_json()
        categories = data['categories']
        
        # Verify each category has required fields
        for category in categories:
            assert 'name' in category
            assert 'display_name' in category
            assert 'probes' in category
            assert isinstance(category['probes'], list)
            
            # Check each probe has required fields
            for probe in category['probes']:
                assert 'name' in probe
                assert 'display_name' in probe
                assert 'category' in probe


class TestScanEndpoints:
    """Test scan management endpoints."""
    
    def test_create_scan_valid(self, client, sample_scan_request):
        """Test POST /api/v1/scans with valid data."""
        response = client.post('/api/v1/scans', 
                             json=sample_scan_request,
                             content_type='application/json')
        
        assert response.status_code == 201
        
        data = response.get_json()
        assert 'scan_id' in data
        assert 'metadata' in data
        
        # Verify metadata structure
        metadata = data['metadata']
        assert metadata['name'] == sample_scan_request['name']
        assert metadata['generator'] == sample_scan_request['generator']
        assert metadata['model_name'] == sample_scan_request['model_name']
    
    def test_get_scan_details(self, client, sample_scan_request):
        """Test GET /api/v1/scans/{scan_id}."""
        # First create a scan
        create_response = client.post('/api/v1/scans', 
                                    json=sample_scan_request,
                                    content_type='application/json')
        assert create_response.status_code == 201
        
        scan_id = create_response.get_json()['scan_id']
        
        # Then retrieve it
        response = client.get(f'/api/v1/scans/{scan_id}')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['metadata']['scan_id'] == scan_id
        assert data['metadata']['name'] == sample_scan_request['name']
    
    def test_list_scans(self, client, sample_scan_request):
        """Test GET /api/v1/scans."""
        # Create a scan first
        client.post('/api/v1/scans', 
                   json=sample_scan_request,
                   content_type='application/json')
        
        response = client.get('/api/v1/scans')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'scans' in data
        assert 'total' in data
        assert 'page' in data
        assert 'per_page' in data
        assert 'has_next' in data
        
        # Should have at least one scan
        assert data['total'] >= 1
        assert len(data['scans']) >= 1
    
    def test_get_nonexistent_scan(self, client):
        """Test GET /api/v1/scans/{nonexistent}."""
        response = client.get('/api/v1/scans/nonexistent-scan-id')
        assert response.status_code == 404
        
        data = response.get_json()
        assert 'error' in data
        assert 'message' in data
    
    def test_scan_persistence_after_creation(self, client, sample_scan_request):
        """Test that scans are properly persisted to disk after creation."""
        import os
        import json
        from app import DATA_DIR
        
        # Create a scan
        create_response = client.post('/api/v1/scans', 
                                    json=sample_scan_request,
                                    content_type='application/json')
        assert create_response.status_code == 201
        
        scan_id = create_response.get_json()['scan_id']
        
        # Verify job file exists on disk
        job_file_path = os.path.join(DATA_DIR, f"job_{scan_id}.json")
        assert os.path.exists(job_file_path), f"Job file should exist at {job_file_path}"
        
        # Verify job file contains correct data
        # Add a small delay to ensure file is written completely
        import time
        time.sleep(0.1)
        
        with open(job_file_path, 'r') as f:
            content = f.read().strip()
            if not content:
                # If file is empty, try waiting a bit longer
                time.sleep(0.5)
                f.seek(0)
                content = f.read().strip()
            
            assert content, f"Job file {job_file_path} should not be empty"
            job_data = json.loads(content)
        
        # Check both 'id' and 'job_id' fields for compatibility
        assert job_data.get('id', job_data.get('job_id')) == scan_id
        assert job_data['generator'] == sample_scan_request['generator']
        assert job_data['model_name'] == sample_scan_request['model_name']
        
        # Check that essential fields are present
        assert job_data.get('probe_categories') == sample_scan_request['probe_categories']
        assert job_data.get('description') == sample_scan_request.get('description')
        
        assert 'created_at' in job_data
        # Status could be 'pending' or 'running' depending on timing
        assert job_data['status'] in ['pending', 'running']
    
    def test_scan_retrieval_from_disk(self, client, sample_scan_request):
        """Test that scans can be retrieved from disk even if not in memory."""
        import os
        import json
        from app import DATA_DIR, JOBS
        
        # Create a scan
        create_response = client.post('/api/v1/scans', 
                                    json=sample_scan_request,
                                    content_type='application/json')
        assert create_response.status_code == 201
        
        scan_id = create_response.get_json()['scan_id']
        
        # Simulate clearing the in-memory jobs dictionary
        # This mimics what could happen during a server restart
        if scan_id in JOBS:
            del JOBS[scan_id]
        
        # Now try to retrieve the scan - it should reload from disk
        response = client.get(f'/api/v1/scans/{scan_id}')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['metadata']['scan_id'] == scan_id
        assert data['metadata']['generator'] == sample_scan_request['generator']
        assert data['metadata']['model_name'] == sample_scan_request['model_name']
        
        # Verify the scan is back in memory
        assert scan_id in JOBS
    
    def test_scan_status_retrieval_from_disk(self, client, sample_scan_request):
        """Test that scan status can be retrieved from disk even if not in memory."""
        import os
        import json
        from app import DATA_DIR, JOBS
        
        # Create a scan
        create_response = client.post('/api/v1/scans', 
                                    json=sample_scan_request,
                                    content_type='application/json')
        assert create_response.status_code == 201
        
        scan_id = create_response.get_json()['scan_id']
        
        # Simulate clearing the in-memory jobs dictionary
        if scan_id in JOBS:
            del JOBS[scan_id]
        
        # Now try to get scan status - it should reload from disk
        response = client.get(f'/api/v1/scans/{scan_id}/status')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['scan_id'] == scan_id
        assert 'status' in data
        assert 'created_at' in data
    
    def test_scan_list_reloads_from_disk(self, client, sample_scan_request):
        """Test that scan list endpoint reloads data from disk when memory is empty."""
        from app import JOBS
        
        # Create a scan
        create_response = client.post('/api/v1/scans', 
                                    json=sample_scan_request,
                                    content_type='application/json')
        assert create_response.status_code == 201
        
        scan_id = create_response.get_json()['scan_id']
        
        # Clear all jobs from memory
        JOBS.clear()
        
        # List scans should reload from disk
        response = client.get('/api/v1/scans')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'scans' in data
        assert data['total'] >= 1
        
        # Find our scan in the list
        scan_found = False
        for scan in data['scans']:
            if scan['scan_id'] == scan_id:
                scan_found = True
                assert scan['generator'] == sample_scan_request['generator']
                assert scan['model_name'] == sample_scan_request['model_name']
                break
        
        assert scan_found, f"Scan {scan_id} should be found in the list after reload"
    
    def test_scan_persistence_error_handling(self, client, sample_scan_request):
        """Test error handling when scan persistence fails."""
        import os
        from unittest.mock import patch
        
        # Mock os.path.join to cause a permission error during file write
        with patch('builtins.open', side_effect=PermissionError("Access denied")):
            response = client.post('/api/v1/scans', 
                                 json=sample_scan_request,
                                 content_type='application/json')
            assert response.status_code == 500
            
            data = response.get_json()
            assert data['error'] == 'scan_persistence_failed'
            assert 'Failed to save scan to disk' in data['message']


class TestErrorHandling:
    """Test API error handling."""
    
    def test_invalid_json(self, client):
        """Test endpoint with invalid JSON."""
        response = client.post('/api/v1/scans',
                             data='invalid json',
                             content_type='application/json')
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'message' in data
        assert 'timestamp' in data
        # Flask converts invalid JSON to a validation error, which is acceptable
        assert data['error'] in ['invalid_json', 'validation_error']
    
    def test_missing_content_type(self, client):
        """Test endpoint without proper content type."""
        response = client.post('/api/v1/scans',
                             data='{"test": "data"}')
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] == 'invalid_content_type'
    
    def test_validation_error(self, client):
        """Test endpoint with validation errors."""
        invalid_data = {
            'generator': 'invalid_generator',
            'model_name': 'test-model'
        }
        
        response = client.post('/api/v1/scans',
                             json=invalid_data,
                             content_type='application/json')
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] == 'validation_error'
        assert 'details' in data
        assert isinstance(data['details'], list)
    
    def test_missing_required_fields(self, client):
        """Test endpoint with missing required fields."""
        incomplete_data = {
            'generator': 'openai'
            # Missing model_name and probe_categories
        }
        
        response = client.post('/api/v1/scans',
                             json=incomplete_data,
                             content_type='application/json')
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] == 'validation_error'
    
    def test_invalid_probe_category(self, client):
        """Test scan creation with invalid probe category."""
        invalid_data = {
            'generator': 'huggingface',
            'model_name': 'gpt2',
            'probe_categories': ['invalid_category']
        }
        
        response = client.post('/api/v1/scans',
                             json=invalid_data,
                             content_type='application/json')
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] == 'validation_error'


class TestRateLimiting:
    """Test rate limiting headers."""
    
    def test_rate_limit_headers(self, client):
        """Test that rate limit headers are present."""
        response = client.get('/api/v1/generators')
        assert response.status_code == 200
        
        # Check rate limit headers are present
        assert 'X-RateLimit-Limit' in response.headers
        assert 'X-RateLimit-Remaining' in response.headers
        assert 'X-RateLimit-Window' in response.headers
        
        # Check header values are valid
        limit = int(response.headers['X-RateLimit-Limit'])
        remaining = int(response.headers['X-RateLimit-Remaining'])
        window = int(response.headers['X-RateLimit-Window'])
        
        assert limit > 0
        assert remaining >= 0
        assert window > 0
    
    def test_rate_limit_consistency(self, client):
        """Test rate limit headers across multiple requests."""
        responses = []
        for _ in range(3):
            response = client.get('/api/v1/info')
            responses.append(response)
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200
            assert 'X-RateLimit-Limit' in response.headers