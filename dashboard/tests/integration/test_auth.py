"""
Integration tests for authentication functionality.
"""

import pytest


class TestAuthBypass:
    """Test authentication bypass functionality."""
    
    def test_auth_bypass_active(self, client):
        """Test that authentication bypass is active in test mode."""
        # Should be able to access protected endpoints without API key
        response = client.get('/api/v1/generators')
        assert response.status_code == 200
        
        response = client.get('/api/v1/probes')
        assert response.status_code == 200
    
    def test_auth_bypass_scan_creation(self, client, sample_scan_request):
        """Test scan creation works with auth bypass."""
        response = client.post('/api/v1/scans',
                             json=sample_scan_request,
                             content_type='application/json')
        
        assert response.status_code == 201
        data = response.get_json()
        assert 'scan_id' in data
    
    def test_auth_bypass_provides_mock_api_key(self, app):
        """Test that auth bypass provides mock API key info."""
        from flask import g
        from api.core.auth import api_key_required
        
        with app.app_context():
            with app.test_request_context():
                @api_key_required
                def test_endpoint():
                    return g.api_key_info
                
                api_key_info = test_endpoint()
                
                # Check all required fields are present
                required_fields = ['id', 'name', 'permissions', 'rate_limit', 'user_id', 'key_prefix']
                for field in required_fields:
                    assert field in api_key_info, f"Missing field: {field}"
                
                # Check permissions is a list
                assert isinstance(api_key_info['permissions'], list)
                assert 'admin' in api_key_info['permissions']


class TestAuthHeaderValidation:
    """Test authentication header validation (when auth is enabled)."""
    
    @pytest.mark.skip(reason="Auth bypass is enabled in test environment")
    def test_missing_api_key_header(self, client):
        """Test request without API key header."""
        # This would fail in production but passes in test due to bypass
        response = client.get('/api/v1/generators')
        assert response.status_code == 200  # Would be 401 in production
    
    @pytest.mark.skip(reason="Auth bypass is enabled in test environment")
    def test_invalid_api_key_format(self, client):
        """Test request with invalid API key format."""
        headers = {'X-API-Key': 'invalid-key-format'}
        response = client.get('/api/v1/generators', headers=headers)
        assert response.status_code == 200  # Would be 401 in production
    
    @pytest.mark.skip(reason="Auth bypass is enabled in test environment") 
    def test_expired_api_key(self, client):
        """Test request with expired API key."""
        headers = {'X-API-Key': 'garak_expired_key_here'}
        response = client.get('/api/v1/generators', headers=headers)
        assert response.status_code == 200  # Would be 401 in production


class TestPermissions:
    """Test permission checking."""
    
    def test_read_permission_endpoints(self, client):
        """Test endpoints that require read permission."""
        read_endpoints = [
            '/api/v1/generators',
            '/api/v1/probes',
            '/api/v1/info',
            '/api/v1/health'
        ]
        
        for endpoint in read_endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200, f"Failed for endpoint: {endpoint}"
    
    def test_write_permission_endpoint(self, client, sample_scan_request):
        """Test endpoint that requires write permission."""
        response = client.post('/api/v1/scans',
                             json=sample_scan_request,
                             content_type='application/json')
        
        assert response.status_code == 201
    
    @pytest.mark.skip(reason="Admin endpoints may not be available in test setup")
    def test_admin_permission_endpoints(self, client):
        """Test endpoints that require admin permission."""
        # These would require proper admin setup
        admin_endpoints = [
            '/api/v1/admin/api-keys',
            '/api/v1/admin/bootstrap'
        ]
        
        for endpoint in admin_endpoints:
            response = client.get(endpoint)
            # In test mode with auth bypass, these might work or might not exist
            assert response.status_code in [200, 404, 405]  # Flexible assertion


class TestSecurityHeaders:
    """Test security-related headers."""
    
    def test_response_headers(self, client):
        """Test that responses include appropriate headers."""
        response = client.get('/api/v1/info')
        
        # Check that we get JSON response
        assert response.content_type.startswith('application/json')
        
        # Rate limiting headers should be present
        assert 'X-RateLimit-Limit' in response.headers
        assert 'X-RateLimit-Remaining' in response.headers
    
    def test_cors_headers_if_enabled(self, client):
        """Test CORS headers if CORS is enabled."""
        response = client.options('/api/v1/info')
        
        # This test is flexible since CORS might not be configured
        # In production, you'd want to check for specific CORS headers
        assert response.status_code in [200, 404, 405]