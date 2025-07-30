"""
Shared utilities for the Garak Dashboard API.

This module contains shared functions and utilities used across
different API modules to eliminate circular dependencies.
"""

import os
import uuid
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional
from flask import request, jsonify, current_app
from pydantic import ValidationError


def get_jobs_data():
    """Get access to the global JOBS dictionary from main app."""
    # Import here to avoid circular imports
    from app import JOBS
    return JOBS


def get_probe_categories():
    """Get access to probe categories from main app."""
    from app import PROBE_CATEGORIES
    return PROBE_CATEGORIES


def get_generators():
    """Get access to generators from main app."""
    from app import GENERATORS
    return GENERATORS


def get_anthropic_models():
    """Get access to Anthropic models from main app."""
    from app import ANTHROPIC_MODELS
    return ANTHROPIC_MODELS


def run_garak_job_wrapper(job_id: str, generator: str, model_name: str, 
                         probes: List[str], api_keys: Dict[str, str], 
                         parallel_attempts: int = 1, rest_config: Dict = None):
    """Wrapper for the run_garak_job function."""
    from app import run_garak_job
    return run_garak_job(job_id, generator, model_name, probes, api_keys, parallel_attempts, rest_config)


def validate_json_request(model_class):
    """Decorator to validate JSON request body using Pydantic model."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                # Import ErrorResponse here to avoid circular imports
                from api.core.models import ErrorResponse
                
                if not request.is_json:
                    return jsonify(ErrorResponse(
                        error="invalid_content_type",
                        message="Content-Type must be application/json"
                    ).model_dump()), 400
                
                # Try to get JSON data (may raise BadRequest for invalid JSON)
                try:
                    json_data = request.get_json()
                except Exception as json_error:
                    return jsonify(ErrorResponse(
                        error="invalid_json",
                        message="Invalid JSON format",
                        details=str(json_error)
                    ).model_dump()), 400
                
                # Validate request data
                request_data = model_class(**json_data)
                # Pass validated data to the view function
                return func(request_data, *args, **kwargs)
                
            except ValidationError as e:
                from api.core.models import ErrorResponse
                
                # Clean validation errors to remove non-serializable objects
                clean_errors = []
                for error in e.errors():
                    clean_error = {
                        'type': error.get('type'),
                        'loc': list(error.get('loc', [])),
                        'msg': error.get('msg'),
                        'input': str(error.get('input', ''))[:200]  # Limit input length
                    }
                    if 'url' in error:
                        clean_error['url'] = error['url']
                    clean_errors.append(clean_error)
                
                return jsonify(ErrorResponse(
                    error="validation_error",
                    message="Request validation failed",
                    details=clean_errors
                ).model_dump()), 400
            except Exception as e:
                from api.core.models import ErrorResponse
                return jsonify(ErrorResponse(
                    error="request_processing_error",
                    message="Failed to process request",
                    details=str(e)
                ).model_dump()), 400
            
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator


def create_error_handler(blueprint_name: str):
    """Create a standardized error handler for API blueprints."""
    def handle_error(error):
        """Global error handler for API."""
        current_app.logger.error(f"{blueprint_name} API error: {str(error)}", exc_info=True)
        
        from api.core.models import ErrorResponse
        return jsonify(ErrorResponse(
            error="internal_server_error",
            message="An unexpected error occurred"
        ).model_dump()), 500
    
    return handle_error


# Enhanced generator information with metadata
GENERATOR_INFO = {
    'openai': {
        'display_name': 'OpenAI',
        'description': 'OpenAI models including GPT-3.5, GPT-4, and others',
        'requires_api_key': True,
        'api_key_env': 'OPENAI_API_KEY',
        'supported_models': [
            'gpt-4', 'gpt-4-turbo', 'gpt-4o', 'gpt-4o-mini',
            'gpt-3.5-turbo', 'gpt-3.5-turbo-instruct',
            'text-davinci-003', 'text-davinci-002'
        ]
    },
    'anthropic': {
        'display_name': 'Anthropic Claude',
        'description': 'Anthropic Claude models via LiteLLM',
        'requires_api_key': True,
        'api_key_env': 'ANTHROPIC_API_KEY',
        'supported_models': None  # Will be populated dynamically
    },
    'huggingface': {
        'display_name': 'Hugging Face',
        'description': 'Open source models from Hugging Face Hub',
        'requires_api_key': False,
        'api_key_env': 'HF_INFERENCE_TOKEN',
        'supported_models': [
            'gpt2', 'microsoft/DialoGPT-medium', 'facebook/blenderbot-400M-distill',
            'EleutherAI/gpt-neo-2.7B', 'EleutherAI/gpt-j-6B',
            'microsoft/DialoGPT-large', 'facebook/blenderbot-1B-distill'
        ]
    },
    'cohere': {
        'display_name': 'Cohere',
        'description': 'Cohere language models',
        'requires_api_key': True,
        'api_key_env': 'COHERE_API_KEY',
        'supported_models': ['command', 'command-light', 'command-nightly']
    },
    'ollama': {
        'display_name': 'Ollama',
        'description': 'Local models via Ollama',
        'requires_api_key': False,
        'api_key_env': None,
        'supported_models': ['llama2', 'mistral', 'codellama', 'vicuna', 'neural-chat']
    },
    'replicate': {
        'display_name': 'Replicate',
        'description': 'Models hosted on Replicate platform',
        'requires_api_key': True,
        'api_key_env': 'REPLICATE_API_TOKEN',
        'supported_models': [
            'meta/llama-2-70b-chat', 'mistralai/mistral-7b-instruct-v0.1',
            'stability-ai/stablelm-tuned-alpha-7b'
        ]
    },
    'vertexai': {
        'display_name': 'Google Vertex AI',
        'description': 'Google Cloud Vertex AI models',
        'requires_api_key': True,
        'api_key_env': 'GOOGLE_APPLICATION_CREDENTIALS',
        'supported_models': ['text-bison', 'chat-bison', 'codechat-bison']
    },
    'llamacpp': {
        'display_name': 'Llama.cpp',
        'description': 'Local GGML/GGUF models via llama.cpp',
        'requires_api_key': False,
        'api_key_env': 'GGML_MAIN_PATH',
        'supported_models': ['Custom GGML/GGUF models']
    },
    'mistral': {
        'display_name': 'Mistral AI',
        'description': 'Mistral AI models',
        'requires_api_key': True,
        'api_key_env': 'MISTRAL_API_KEY',
        'supported_models': ['mistral-tiny', 'mistral-small', 'mistral-medium']
    },
    'litellm': {
        'display_name': 'LiteLLM',
        'description': 'Universal LLM interface supporting multiple providers',
        'requires_api_key': True,
        'api_key_env': 'Various (depends on model)',
        'supported_models': ['Supports 100+ models from various providers']
    }
}


# Enhanced category descriptions
PROBE_CATEGORY_DESCRIPTIONS = {
    'dan': {
        'display_name': 'DAN (Do Anything Now)',
        'description': 'Jailbreaking attacks that attempt to bypass safety guidelines'
    },
    'security': {
        'display_name': 'Security Vulnerabilities',
        'description': 'Tests for prompt injection, data leakage, and security exploits'
    },
    'privacy': {
        'display_name': 'Privacy & Data Leakage',
        'description': 'Tests for training data memorization and private information exposure'
    },
    'toxicity': {
        'display_name': 'Toxicity & Harmful Content',
        'description': 'Tests for generation of toxic, harmful, or inappropriate content'
    },
    'hallucination': {
        'display_name': 'Hallucination & Misinformation',
        'description': 'Tests for factual accuracy and tendency to generate false information'
    },
    'performance': {
        'display_name': 'Performance & Reliability',
        'description': 'Tests for consistent behavior and response quality'
    },
    'robustness': {
        'display_name': 'Robustness & Adversarial',
        'description': 'Tests resilience against adversarial inputs and encoding attacks'
    },
    'ethics': {
        'display_name': 'Ethical Considerations',
        'description': 'Tests for biased or unethical behavior patterns'
    },
    'stereotype': {
        'display_name': 'Bias & Stereotyping',
        'description': 'Tests for stereotypical or biased outputs'
    }
}


def get_generator_info(generator_name: str) -> Dict[str, Any]:
    """Get enhanced information about a specific generator."""
    generators_map = get_generators()
    
    if generator_name not in generators_map:
        return None
    
    info = GENERATOR_INFO.get(generator_name, {
        'display_name': generators_map[generator_name],
        'description': f'{generators_map[generator_name]} models',
        'requires_api_key': True,
        'api_key_env': None,
        'supported_models': []
    })
    
    # Always include the generator name
    info['name'] = generator_name
    
    # Handle dynamic model lists
    if generator_name == 'anthropic' and info['supported_models'] is None:
        info['supported_models'] = get_anthropic_models()
    
    return info


def get_probe_category_info(category_name: str) -> Dict[str, str]:
    """Get enhanced information about a probe category."""
    info = PROBE_CATEGORY_DESCRIPTIONS.get(category_name, {
        'display_name': category_name.title(),
        'description': f'Probes in the {category_name} category'
    })
    # Always include the category name
    info['name'] = category_name
    return info