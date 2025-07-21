#!/usr/bin/env python3
"""
Tests for the Gemini generator.
"""

import os
import pytest
import httpx
from unittest.mock import patch, MagicMock
from garak.generators.gemini import GeminiGenerator

DEFAULT_MODEL_NAME = "gemini-1.5-pro"

@pytest.fixture
def set_fake_env(request) -> None:
    """Set a fake API key for testing."""
    stored_env = os.getenv(GeminiGenerator.ENV_VAR, None)

    def restore_env():
        if stored_env is not None:
            os.environ[GeminiGenerator.ENV_VAR] = stored_env
        else:
            if GeminiGenerator.ENV_VAR in os.environ:
                del os.environ[GeminiGenerator.ENV_VAR]

    os.environ[GeminiGenerator.ENV_VAR] = os.path.abspath(__file__)
    request.addfinalizer(restore_env)

@pytest.mark.usefixtures("set_fake_env")
def test_gemini_generator_init():
    """Test initialization of the Gemini generator."""
    generator = GeminiGenerator(name=DEFAULT_MODEL_NAME)
    assert generator.name == DEFAULT_MODEL_NAME
    assert generator.generator_family_name == "gemini"
    assert generator.supports_multiple_generations is True
    assert generator.ENV_VAR == "GOOGLE_API_KEY"

@pytest.mark.usefixtures("set_fake_env")
def test_gemini_generator_with_mock(monkeypatch, gemini_compat_mocks):
    """Test the Gemini generator with a mocked response."""
    # Create a mock for the GenerativeModel class
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "This is a mock response from the Gemini model for testing purposes."
    mock_model.generate_content.return_value = mock_response
    
    # Patch the GenerativeModel constructor
    def mock_generative_model(*args, **kwargs):
        return mock_model
    
    # Patch the genai.configure function
    mock_configure = MagicMock()
    
    # Apply the patches
    monkeypatch.setattr("google.generativeai.GenerativeModel", mock_generative_model)
    monkeypatch.setattr("google.generativeai.configure", mock_configure)
    
    # Create the generator and test it
    generator = GeminiGenerator(name=DEFAULT_MODEL_NAME)
    output = generator._call_model("Hello Gemini!", generations_this_call=1)
    
    # Verify the results
    assert len(output) == 1
    assert output[0] == "This is a mock response from the Gemini model for testing purposes."
    mock_model.generate_content.assert_called_once_with("Hello Gemini!")

@pytest.mark.usefixtures("set_fake_env")
def test_gemini_generator_multiple_generations(monkeypatch):
    """Test the Gemini generator with multiple generations."""
    # Create a mock for the GenerativeModel class
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "This is a mock response from the Gemini model for testing purposes."
    mock_model.generate_content.return_value = mock_response
    
    # Patch the GenerativeModel constructor
    def mock_generative_model(*args, **kwargs):
        return mock_model
    
    # Patch the genai.configure function
    mock_configure = MagicMock()
    
    # Apply the patches
    monkeypatch.setattr("google.generativeai.GenerativeModel", mock_generative_model)
    monkeypatch.setattr("google.generativeai.configure", mock_configure)
    
    # Create the generator and test it
    generator = GeminiGenerator(name=DEFAULT_MODEL_NAME)
    output = generator._call_model("Hello Gemini!", generations_this_call=3)
    
    # Verify the results
    assert len(output) == 3
    assert all(response == "This is a mock response from the Gemini model for testing purposes." for response in output)
    assert mock_model.generate_content.call_count == 3

@pytest.mark.usefixtures("set_fake_env")
def test_gemini_generator_error_handling(monkeypatch):
    """Test error handling in the Gemini generator."""
    # Create a mock for the GenerativeModel class
    mock_model = MagicMock()
    mock_model.generate_content.side_effect = Exception("Test error")
    
    # Patch the GenerativeModel constructor
    def mock_generative_model(*args, **kwargs):
        return mock_model
    
    # Patch the genai.configure function
    mock_configure = MagicMock()
    
    # Apply the patches
    monkeypatch.setattr("google.generativeai.GenerativeModel", mock_generative_model)
    monkeypatch.setattr("google.generativeai.configure", mock_configure)
    
    # Create the generator and test it
    generator = GeminiGenerator(name=DEFAULT_MODEL_NAME)
    output = generator._call_model("Hello Gemini!", generations_this_call=1)
    
    # Verify the results
    assert len(output) == 1
    assert output[0] is None
    mock_model.generate_content.assert_called_once_with("Hello Gemini!")

@pytest.mark.skipif(
    os.getenv(GeminiGenerator.ENV_VAR, None) is None,
    reason=f"Gemini API key is not set in {GeminiGenerator.ENV_VAR}",
)
def test_gemini_live():
    """Test the Gemini generator with a live API call.
    
    This test is skipped if the API key is not set.
    """
    generator = GeminiGenerator(name=DEFAULT_MODEL_NAME)
    output = generator.generate("Hello Gemini!")
    assert len(output) == 1  # expect 1 generation by default
    assert isinstance(output[0], str)  # expect a string response
    print("Live test passed!")
