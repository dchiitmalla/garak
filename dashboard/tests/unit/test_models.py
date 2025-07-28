"""
Unit tests for Pydantic models.
"""

import pytest
from datetime import datetime
from typing import Dict, Any


class TestPydanticModels:
    """Test Pydantic model functionality."""
    
    def test_error_response_basic(self, api_models):
        """Test basic ErrorResponse functionality."""
        ErrorResponse = api_models['ErrorResponse']
        
        error = ErrorResponse(error='test', message='test message')
        assert error.error == 'test'
        assert error.message == 'test message'
        assert error.timestamp is not None
        
        # Test serialization
        data = error.model_dump()
        assert isinstance(data, dict)
        assert data['error'] == 'test'
        assert data['message'] == 'test message'
    
    def test_error_response_with_details(self, api_models):
        """Test ErrorResponse with details field."""
        ErrorResponse = api_models['ErrorResponse']
        
        # Test with dict details
        error1 = ErrorResponse(
            error='test', 
            message='test message', 
            details={'field': 'value'}
        )
        assert isinstance(error1.details, dict)
        
        # Test with list details (validation errors)
        error2 = ErrorResponse(
            error='validation_error',
            message='Validation failed',
            details=[{'field': 'test', 'error': 'required'}]
        )
        assert isinstance(error2.details, list)
        
        # Test serialization
        data = error2.model_dump()
        assert isinstance(data['details'], list)
    
    def test_create_scan_request_basic(self, api_models):
        """Test CreateScanRequest basic functionality."""
        CreateScanRequest = api_models['CreateScanRequest']
        
        scan_req = CreateScanRequest(
            generator='huggingface',
            model_name='gpt2',
            probe_categories=['dan'],
            api_keys={}
        )
        
        assert scan_req.generator == 'huggingface'
        assert scan_req.model_name == 'gpt2'
        assert scan_req.probe_categories == ['dan']
        assert scan_req.parallel_attempts == 1  # default value
    
    def test_create_scan_request_with_options(self, api_models):
        """Test CreateScanRequest with all options."""
        CreateScanRequest = api_models['CreateScanRequest']
        
        scan_req = CreateScanRequest(
            generator='openai',
            model_name='gpt-4',
            probe_categories=['dan', 'security'],
            probes=['dan.DAN_Jailbreak'],
            api_keys={'openai_api_key': 'sk-test'},
            parallel_attempts=3,
            name='Full Test Scan',
            description='A comprehensive test scan'
        )
        
        assert scan_req.generator == 'openai'
        assert scan_req.model_name == 'gpt-4'
        assert scan_req.probe_categories == ['dan', 'security']
        assert scan_req.probes == ['dan.DAN_Jailbreak']
        assert scan_req.parallel_attempts == 3
        assert scan_req.name == 'Full Test Scan'
        assert scan_req.description == 'A comprehensive test scan'
    
    def test_create_scan_request_validation(self, api_models):
        """Test CreateScanRequest validation."""
        CreateScanRequest = api_models['CreateScanRequest']
        
        # Test invalid generator
        with pytest.raises(ValueError, match="Invalid generator"):
            CreateScanRequest(
                generator='invalid_generator',
                model_name='test-model',
                probe_categories=['dan']
            )
        
        # Test invalid probe category
        with pytest.raises(ValueError, match="Invalid probe category"):
            CreateScanRequest(
                generator='huggingface',
                model_name='gpt2',
                probe_categories=['invalid_category']
            )
        
        # Test invalid parallel_attempts
        with pytest.raises(ValueError):
            CreateScanRequest(
                generator='huggingface',
                model_name='gpt2',
                probe_categories=['dan'],
                parallel_attempts=0  # Should be >= 1
            )
    
    def test_scan_metadata(self, api_models):
        """Test ScanMetadata model."""
        ScanMetadata = api_models['ScanMetadata']
        ScanStatus = api_models['ScanStatus']
        
        metadata = ScanMetadata(
            scan_id='test-scan-123',
            generator='test.Blank',
            model_name='test-model',
            probe_categories=['dan'],
            probes=['dan.DAN_Jailbreak'],
            status=ScanStatus.PENDING,
            created_at=datetime.utcnow(),
            parallel_attempts=1
        )
        
        assert metadata.scan_id == 'test-scan-123'
        assert metadata.status == ScanStatus.PENDING
        assert isinstance(metadata.created_at, datetime)
    
    def test_generator_info(self, api_models):
        """Test GeneratorInfo model."""
        GeneratorInfo = api_models['GeneratorInfo']
        
        generator = GeneratorInfo(
            name='openai',
            display_name='OpenAI',
            description='OpenAI models',
            requires_api_key=True,
            supported_models=['gpt-4', 'gpt-3.5-turbo']
        )
        
        assert generator.name == 'openai'
        assert generator.display_name == 'OpenAI'
        assert generator.requires_api_key is True
        assert 'gpt-4' in generator.supported_models
    
    def test_api_key_info(self, api_models):
        """Test APIKeyInfo model."""
        APIKeyInfo = api_models['APIKeyInfo']
        PermissionType = api_models['PermissionType']
        
        api_key_info = APIKeyInfo(
            id=1,
            key_prefix='garak_abc...',
            name='Test Key',
            description='A test API key',
            permissions=[PermissionType.READ, PermissionType.WRITE],
            rate_limit=100,
            usage_count=0,
            created_at=datetime.utcnow(),
            is_active=True
        )
        
        assert api_key_info.id == 1
        assert api_key_info.key_prefix == 'garak_abc...'
        assert PermissionType.READ in api_key_info.permissions
        assert api_key_info.rate_limit == 100
    
    def test_model_serialization(self, api_models):
        """Test that all models can be serialized to JSON."""
        CreateScanRequest = api_models['CreateScanRequest']
        ErrorResponse = api_models['ErrorResponse']
        
        # Test scan request serialization
        scan_req = CreateScanRequest(
            generator='huggingface',
            model_name='gpt2',
            probe_categories=['dan'],
            api_keys={'hf_token': 'test_value'}
        )
        
        data = scan_req.model_dump()
        assert isinstance(data, dict)
        assert 'generator' in data
        assert 'model_name' in data
        
        # Test error response serialization
        error = ErrorResponse(
            error='test_error',
            message='Test message',
            details={'extra': 'info'}
        )
        
        data = error.model_dump()
        assert isinstance(data, dict)
        assert data['error'] == 'test_error'
        assert isinstance(data['details'], dict)


class TestEnums:
    """Test enum functionality."""
    
    def test_scan_status_enum(self, api_models):
        """Test ScanStatus enum."""
        ScanStatus = api_models['ScanStatus']
        
        assert ScanStatus.PENDING == "pending"
        assert ScanStatus.RUNNING == "running"
        assert ScanStatus.COMPLETED == "completed"
        assert ScanStatus.FAILED == "failed"
        assert ScanStatus.CANCELLED == "cancelled"
    
    def test_permission_type_enum(self, api_models):
        """Test PermissionType enum."""
        PermissionType = api_models['PermissionType']
        
        assert PermissionType.READ == "read"
        assert PermissionType.WRITE == "write"
        assert PermissionType.ADMIN == "admin"
    
    def test_report_type_enum(self, api_models):
        """Test ReportType enum."""
        ReportType = api_models['ReportType']
        
        assert ReportType.JSON == "json"
        assert ReportType.JSONL == "jsonl"
        assert ReportType.HTML == "html"
        assert ReportType.HITS == "hits"