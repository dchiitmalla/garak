"""
Unit tests for utility functions.
"""

import pytest


class TestGeneratorUtils:
    """Test generator utility functions."""
    
    def test_get_generators_basic(self, utils):
        """Test basic generator listing."""
        generators = utils['get_generators']()
        
        assert isinstance(generators, dict)
        assert len(generators) > 0
        
        # Check for common generators
        assert 'openai' in generators
        assert 'huggingface' in generators
    
    def test_get_generator_info_openai(self, utils):
        """Test getting OpenAI generator info."""
        openai_info = utils['get_generator_info']('openai')
        
        assert openai_info is not None
        assert openai_info['name'] == 'openai'
        assert openai_info['display_name'] == 'OpenAI'
        assert openai_info['requires_api_key'] is True
        assert len(openai_info['supported_models']) > 0
        assert 'gpt-4' in openai_info['supported_models']
    
    def test_get_generator_info_huggingface(self, utils):
        """Test getting Hugging Face generator info."""
        hf_info = utils['get_generator_info']('huggingface')
        
        assert hf_info is not None
        assert hf_info['name'] == 'huggingface'
        assert hf_info['display_name'] == 'Hugging Face'
        assert 'requires_api_key' in hf_info
        assert len(hf_info['supported_models']) > 0
    
    def test_get_generator_info_nonexistent(self, utils):
        """Test getting info for nonexistent generator."""
        invalid_info = utils['get_generator_info']('nonexistent')
        assert invalid_info is None
    
    def test_get_generator_info_anthropic(self, utils):
        """Test getting Anthropic generator info."""
        anthropic_info = utils['get_generator_info']('anthropic')
        
        if anthropic_info:  # May not be available in all environments
            assert anthropic_info['name'] == 'anthropic'
            assert anthropic_info['display_name'] == 'Anthropic Claude'
            assert anthropic_info['requires_api_key'] is True


class TestProbeUtils:
    """Test probe utility functions."""
    
    def test_get_probe_categories_basic(self, utils):
        """Test basic probe category listing."""
        categories = utils['get_probe_categories']()
        
        assert isinstance(categories, dict)
        assert len(categories) > 0
        
        # Check for common categories
        assert 'dan' in categories
        assert 'security' in categories
    
    def test_get_probe_category_info_dan(self, utils):
        """Test getting DAN category info."""
        dan_info = utils['get_probe_category_info']('dan')
        
        assert dan_info is not None
        assert dan_info['name'] == 'dan'
        assert dan_info['display_name'] == 'DAN (Do Anything Now)'
        assert 'jailbreaking' in dan_info['description'].lower()
    
    def test_get_probe_category_info_security(self, utils):
        """Test getting security category info."""
        security_info = utils['get_probe_category_info']('security')
        
        assert security_info is not None
        assert security_info['name'] == 'security'
        assert security_info['display_name'] == 'Security Vulnerabilities'
        assert 'security' in security_info['description'].lower()
    
    def test_get_probe_category_info_nonexistent(self, utils):
        """Test getting info for nonexistent category."""
        info = utils['get_probe_category_info']('nonexistent_category')
        
        # Should return default info structure
        assert info['name'] == 'nonexistent_category'
        assert info['display_name'] == 'Nonexistent_Category'
        assert 'nonexistent_category' in info['description']


class TestAnthropicModels:
    """Test Anthropic models utility."""
    
    def test_get_anthropic_models(self, utils):
        """Test getting Anthropic models."""
        models = utils['get_anthropic_models']()
        
        # Should return a list (may be empty if not configured)
        assert isinstance(models, list)