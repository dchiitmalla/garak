#!/usr/bin/env python3
"""
Generator for Google's Gemini models using the Google Generative AI Python client.
"""

import os
import backoff
from typing import List, Union

import google.generativeai as genai
from google.api_core.exceptions import GoogleAPIError

from garak.generators.base import Generator
import garak._config as _config


class GeminiGenerator(Generator):
    """
    Interface for Google's Gemini models using the Google Generative AI Python client.
    Expects API key in GOOGLE_API_KEY environment variable.
    """

    generator_family_name = "gemini"
    fullname = "Google Gemini"
    supports_multiple_generations = True
    ENV_VAR = "GOOGLE_API_KEY"
    DEFAULT_PARAMS = Generator.DEFAULT_PARAMS | {
        "name": "gemini-1.5-pro",
        "temperature": 0.7,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 1024,
    }

    # avoid attempt to pickle the model attribute
    def __getstate__(self) -> object:
        self._clear_model()
        return dict(self.__dict__)

    # restore the model attribute
    def __setstate__(self, d) -> object:
        self.__dict__.update(d)
        self._load_model()

    def _load_model(self):
        """Load the Gemini model."""
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(
            model_name=self.name,
            generation_config={
                "temperature": self.temperature,
                "top_p": self.top_p,
                "top_k": self.top_k,
                "max_output_tokens": self.max_output_tokens,
            }
        )

    def _clear_model(self):
        """Clear the model to avoid pickling issues."""
        self.model = None

    def __init__(self, name="", config_root=_config):
        """Initialize the Gemini generator."""
        # Initialize default parameters before calling super().__init__
        self.temperature = self.DEFAULT_PARAMS["temperature"]
        self.top_p = self.DEFAULT_PARAMS["top_p"]
        self.top_k = self.DEFAULT_PARAMS["top_k"]
        self.max_output_tokens = self.DEFAULT_PARAMS["max_output_tokens"]
        
        # Call parent init which will load config and override defaults
        super().__init__(name, config_root)
        
        # Validate and get API key
        if not hasattr(self, "api_key") or not self.api_key:
            self.api_key = os.environ.get(self.ENV_VAR)
            if not self.api_key:
                raise ValueError(f"API key not found in environment variable {self.ENV_VAR}")
        
        # Load the model
        self._load_model()

    @backoff.on_exception(backoff.expo, GoogleAPIError, max_tries=5)
    def _call_model(self, prompt: str, generations_this_call: int = 1) -> List[Union[str, None]]:
        """Call the Gemini model with the given prompt."""
        responses = []
        
        for _ in range(generations_this_call):
            try:
                response = self.model.generate_content(prompt)
                if hasattr(response, "text") and response.text:
                    responses.append(response.text)
                else:
                    responses.append(None)
            except Exception as e:
                print(f"Error generating response: {e}")
                responses.append(None)
        
        return responses


DEFAULT_CLASS = "GeminiGenerator"
