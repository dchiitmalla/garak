"""
Unit tests for probe error handling fixes.

Tests that probe execution errors are handled gracefully and don't cause
job failures or unexpected behavior.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add the parent garak directory to the path for imports
GARAK_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
sys.path.insert(0, GARAK_ROOT)


class TestAutoDanProbeErrorHandling:
    """Test AutoDAN probe error handling for different generator types."""
    
    def test_autodan_probe_with_non_huggingface_generator(self):
        """Test that AutoDAN probe gracefully handles non-HuggingFace generators."""
        # Import here to avoid module loading issues during test collection
        from garak.probes.dan import AutoDAN
        
        # Create a mock generator that's not a HuggingFace model
        mock_generator = Mock()
        mock_generator.__class__.__name__ = 'OpenAIGenerator'
        
        # Create the probe
        probe = AutoDAN()
        
        # Test that it returns empty list for non-HF generator
        result = list(probe.probe(mock_generator))
        
        # Should return empty list, not raise exception
        assert result == []
        assert len(result) == 0
    
    def test_autodan_probe_with_huggingface_generator_success(self):
        """Test that AutoDAN probe works correctly with HuggingFace generators."""
        from garak.probes.dan import AutoDAN
        from garak.generators.huggingface import Model
        
        # Create a mock HuggingFace generator
        mock_hf_generator = Mock(spec=Model)
        mock_hf_generator.name = "test-model"
        
        # Create the probe
        probe = AutoDAN()
        
        # Mock successful autodan generation
        mock_outputs = ["test prompt 1", "test prompt 2"]
        
        with patch('garak.resources.autodan.autodan_generate') as mock_generate:
            mock_generate.return_value = mock_outputs
            
            # Mock the language provider and other dependencies
            probe.langprovider = Mock()
            probe.langprovider.get_text.return_value = mock_outputs
            
            # Mock the _mint_attempt method
            mock_attempt = Mock()
            probe._mint_attempt = Mock(return_value=mock_attempt)
            
            # Mock the _buff_hook and _execute_all methods
            probe._buff_hook = Mock(return_value=[mock_attempt, mock_attempt])
            probe._execute_all = Mock(return_value=[mock_attempt, mock_attempt])
            
            # Test that it works correctly with HF generator
            result = list(probe.probe(mock_hf_generator))
            
            # Should return the processed attempts
            assert len(result) == 2
            mock_generate.assert_called_once()
    
    def test_autodan_probe_with_huggingface_generator_failure(self):
        """Test that AutoDAN probe handles generation errors gracefully."""
        from garak.probes.dan import AutoDAN
        from garak.generators.huggingface import Model
        
        # Create a mock HuggingFace generator
        mock_hf_generator = Mock(spec=Model)
        mock_hf_generator.name = "test-model"
        
        # Create the probe
        probe = AutoDAN()
        
        # Mock the autodan_generate function to raise an exception
        with patch('garak.resources.autodan.autodan_generate') as mock_generate:
            mock_generate.side_effect = Exception("AutoDAN generation failed")
            
            # Test that it handles errors gracefully
            result = list(probe.probe(mock_hf_generator))
            
            # Should return empty list when generation fails
            assert result == []
            mock_generate.assert_called_once()
    
    def test_autodan_probe_type_checking(self):
        """Test that AutoDAN probe correctly identifies generator types."""
        from garak.probes.dan import AutoDAN
        from garak.generators.huggingface import Model
        
        # Test with various generator types
        generators_to_test = [
            (Mock(), False),  # Generic mock - not HF
            (Mock(spec=Model), True),  # HF Model spec - is HF
            (Mock(__class__=Mock(__name__='OpenAIGenerator')), False),  # OpenAI - not HF
        ]
        
        for generator, should_be_hf in generators_to_test:
            probe = AutoDAN()
            
            # The probe should identify HF models correctly
            result = list(probe.probe(generator))
            
            if should_be_hf:
                # For HF models, we need to mock the autodan generation
                with patch('garak.resources.autodan.autodan_generate') as mock_generate:
                    mock_generate.return_value = None  # Simulate no outputs
                    result = list(probe.probe(generator))
                    assert result == []  # Should return empty but not crash
            else:
                # For non-HF models, should return empty immediately
                assert result == []


class TestProbeExecutionRobustness:
    """Test that probe execution is robust against various error conditions."""
    
    def test_probe_import_error_handling(self):
        """Test that missing probe dependencies don't crash the system."""
        # This would test that if a probe can't be imported, it's skipped gracefully
        # Implementation would depend on how the dashboard handles probe loading
        pass
    
    def test_probe_execution_timeout_handling(self):
        """Test that probe execution timeouts are handled gracefully."""
        # This would test timeout handling for long-running probes
        # Implementation would depend on timeout mechanisms in place
        pass


# Add pytest markers for the test classes
pytestmark = pytest.mark.unit


class TestJobExecutionErrorHandling:
    """Test job execution error handling improvements."""
    
    def test_job_script_error_handling(self):
        """Test that the job script correctly handles garak execution errors."""
        from app import run_garak_job
        import tempfile
        import os
        
        # This is a more complex integration test that would require
        # mocking the subprocess execution and file system operations
        pass
    
    def test_logging_configuration(self):
        """Test that logging is configured to prevent recursive issues."""
        import logging
        
        # Test that HTTP client loggers are set to appropriate levels
        httpcore_logger = logging.getLogger('httpcore')
        httpx_logger = logging.getLogger('httpx')
        urllib3_logger = logging.getLogger('urllib3')
        
        # These should be set to WARNING level to prevent debug spam
        assert httpcore_logger.level >= logging.WARNING
        assert httpx_logger.level >= logging.WARNING
        assert urllib3_logger.level >= logging.WARNING