"""
Metadata endpoints for Garak Dashboard public API.

This module provides endpoints for discovering available generators,
probes, models, and other metadata needed to construct scan requests.
"""

from flask import Blueprint, jsonify, current_app
from typing import List, Dict, Any

from api.core.auth import read_required
from api.core.rate_limiter import rate_limit
from api.core.models import GeneratorInfo, ProbeCategory, ProbeInfo, ErrorResponse, HealthResponse
from api.core.utils import (
    get_probe_categories, get_generators, get_anthropic_models, get_jobs_data,
    get_generator_info, get_probe_category_info, create_error_handler
)

# Blueprint for metadata endpoints
api_metadata = Blueprint('api_metadata', __name__, url_prefix='/api/v1')


# Utility functions are now imported from api.core.utils


@api_metadata.errorhandler(Exception)
def handle_metadata_error(error):
    """Global error handler for metadata API."""
    current_app.logger.error(f"Metadata API error: {str(error)}", exc_info=True)
    
    return jsonify(ErrorResponse(
        error="internal_server_error",
        message="An unexpected error occurred"
    ).model_dump()), 500


# Generator and Model Discovery

@api_metadata.route('/generators', methods=['GET'])
@read_required
@rate_limit(limit=100, window=60)
def list_generators():
    """List all available model generators."""
    try:
        generators_map = get_generators()
        
        # Enhanced generator information with additional metadata
        generators_info = {
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
                'supported_models': get_anthropic_models()
            },
            'huggingface': {
                'display_name': 'Hugging Face',
                'description': 'Open source models from Hugging Face Hub',
                'requires_api_key': False,
                'api_key_env': 'HF_INFERENCE_TOKEN',
                'supported_models': [
                    'gpt2', 'microsoft/DialoGPT-medium', 'facebook/blenderbot-400M-distill',
                    'EleutherAI/gpt-neo-2.7B', 'EleutherAI/gpt-j-6B'
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
                'supported_models': ['llama2', 'mistral', 'codellama', 'vicuna']
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
        
        generators = []
        for name, display_name in generators_map.items():
            info = generators_info.get(name, {
                'display_name': display_name,
                'description': f'{display_name} models',
                'requires_api_key': True,
                'api_key_env': None,
                'supported_models': []
            })
            
            generator = GeneratorInfo(
                name=name,
                display_name=info['display_name'],
                description=info['description'],
                requires_api_key=info['requires_api_key'],
                supported_models=info['supported_models']
            )
            generators.append(generator)
        
        return jsonify({
            'generators': [gen.model_dump() for gen in generators],
            'total': len(generators)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error listing generators: {str(e)}")
        return jsonify(ErrorResponse(
            error="generator_list_failed",
            message="Failed to list available generators"
        ).model_dump()), 500


@api_metadata.route('/generators/<generator_name>', methods=['GET'])
@read_required
@rate_limit(limit=100, window=60)
def get_generator(generator_name: str):
    """Get detailed information about a specific generator."""
    try:
        generators_map = get_generators()
        
        if generator_name not in generators_map:
            return jsonify(ErrorResponse(
                error="generator_not_found",
                message=f"Generator '{generator_name}' not found"
            ).model_dump()), 404
        
        # Enhanced generator information (same as in list_generators)
        generators_info = {
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
                'supported_models': get_anthropic_models()
            },
            'huggingface': {
                'display_name': 'Hugging Face',
                'description': 'Open source models from Hugging Face Hub',
                'requires_api_key': False,
                'api_key_env': 'HF_INFERENCE_TOKEN',
                'supported_models': [
                    'gpt2', 'microsoft/DialoGPT-medium', 'facebook/blenderbot-400M-distill',
                    'EleutherAI/gpt-neo-2.7B', 'EleutherAI/gpt-j-6B'
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
                'supported_models': ['llama2', 'mistral', 'codellama', 'vicuna']
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
        
        display_name = generators_map[generator_name]
        info = generators_info.get(generator_name, {
            'display_name': display_name,
            'description': f'{display_name} models',
            'requires_api_key': True,
            'api_key_env': None,
            'supported_models': []
        })
        
        generator = GeneratorInfo(
            name=generator_name,
            display_name=info['display_name'],
            description=info['description'],
            requires_api_key=info['requires_api_key'],
            supported_models=info['supported_models']
        )
        
        return jsonify(generator.model_dump())
        
    except Exception as e:
        current_app.logger.error(f"Error getting generator {generator_name}: {str(e)}")
        return jsonify(ErrorResponse(
            error="generator_fetch_failed",
            message=f"Failed to get generator '{generator_name}'"
        ).model_dump()), 500


@api_metadata.route('/generators/<generator_name>/models', methods=['GET'])
@read_required
@rate_limit(limit=100, window=60)
def list_generator_models(generator_name: str):
    """List available models for a specific generator."""
    try:
        generators_map = get_generators()
        
        if generator_name not in generators_map:
            return jsonify(ErrorResponse(
                error="generator_not_found",
                message=f"Generator '{generator_name}' not found"
            ).model_dump()), 404
        
        # Get models based on generator type
        models = []
        
        if generator_name == 'anthropic':
            models = get_anthropic_models()
        elif generator_name == 'openai':
            models = [
                'gpt-4', 'gpt-4-turbo', 'gpt-4o', 'gpt-4o-mini',
                'gpt-3.5-turbo', 'gpt-3.5-turbo-instruct',
                'text-davinci-003', 'text-davinci-002'
            ]
        elif generator_name == 'huggingface':
            models = [
                'gpt2', 'microsoft/DialoGPT-medium', 'facebook/blenderbot-400M-distill',
                'EleutherAI/gpt-neo-2.7B', 'EleutherAI/gpt-j-6B',
                'microsoft/DialoGPT-large', 'facebook/blenderbot-1B-distill'
            ]
        elif generator_name == 'cohere':
            models = ['command', 'command-light', 'command-nightly']
        elif generator_name == 'ollama':
            models = ['llama2', 'mistral', 'codellama', 'vicuna', 'neural-chat']
        elif generator_name == 'replicate':
            models = [
                'meta/llama-2-70b-chat', 'mistralai/mistral-7b-instruct-v0.1',
                'stability-ai/stablelm-tuned-alpha-7b'
            ]
        elif generator_name == 'vertexai':
            models = ['text-bison', 'chat-bison', 'codechat-bison']
        elif generator_name == 'mistral':
            models = ['mistral-tiny', 'mistral-small', 'mistral-medium']
        else:
            models = ['Custom models supported']
        
        return jsonify({
            'generator': generator_name,
            'models': models,
            'total': len(models)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error listing models for {generator_name}: {str(e)}")
        return jsonify(ErrorResponse(
            error="model_list_failed",
            message=f"Failed to list models for generator '{generator_name}'"
        ).model_dump()), 500


# Probe Discovery

@api_metadata.route('/probes', methods=['GET'])
@read_required
@rate_limit(limit=100, window=60)
def list_probe_categories():
    """List all available probe categories and their individual probes."""
    try:
        probe_categories_map = get_probe_categories()
        
        # Enhanced category descriptions
        category_descriptions = {
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
        
        categories = []
        for category_name, probes_list in probe_categories_map.items():
            info = category_descriptions.get(category_name, {
                'display_name': category_name.title(),
                'description': f'Probes in the {category_name} category'
            })
            
            # Convert probe names to ProbeInfo objects
            probe_infos = []
            for probe_name in probes_list:
                probe_info = ProbeInfo(
                    name=probe_name,
                    display_name=probe_name.split('.')[-1],  # Get class name
                    category=category_name,
                    description=f'Security probe: {probe_name}',
                    recommended_detectors=[]  # Would need to query actual probe classes
                )
                probe_infos.append(probe_info)
            
            category = ProbeCategory(
                name=category_name,
                display_name=info['display_name'],
                description=info['description'],
                probes=probe_infos
            )
            categories.append(category)
        
        return jsonify({
            'categories': [cat.model_dump() for cat in categories],
            'total_categories': len(categories),
            'total_probes': sum(len(cat.probes) for cat in categories)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error listing probe categories: {str(e)}")
        return jsonify(ErrorResponse(
            error="probe_list_failed",
            message="Failed to list available probe categories"
        ).model_dump()), 500


@api_metadata.route('/probes/<category_name>', methods=['GET'])
@read_required
@rate_limit(limit=100, window=60)
def list_category_probes(category_name: str):
    """List all probes in a specific category."""
    try:
        probe_categories_map = get_probe_categories()
        
        if category_name not in probe_categories_map:
            return jsonify(ErrorResponse(
                error="category_not_found",
                message=f"Probe category '{category_name}' not found"
            ).model_dump()), 404
        
        probes_list = probe_categories_map[category_name]
        
        # Convert to ProbeInfo objects
        probes = []
        for probe_name in probes_list:
            probe_info = ProbeInfo(
                name=probe_name,
                display_name=probe_name.split('.')[-1],
                category=category_name,
                description=f'Security probe: {probe_name}',
                recommended_detectors=[]
            )
            probes.append(probe_info)
        
        return jsonify({
            'category': category_name,
            'probes': [probe.model_dump() for probe in probes],
            'total': len(probes)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error listing probes for category {category_name}: {str(e)}")
        return jsonify(ErrorResponse(
            error="category_probe_list_failed",
            message=f"Failed to list probes for category '{category_name}'"
        ).model_dump()), 500


# API Information and Health

@api_metadata.route('/info', methods=['GET'])
@rate_limit(limit=1000, window=60)  # High limit for info endpoint
def api_info():
    """Get general API information and capabilities."""
    try:
        return jsonify({
            'api_version': 'v1',
            'version': 'v1',  # Add version field for compatibility
            'service': 'Garak LLM Security Scanner',
            'description': 'Public API for running AI red-teaming security scans',
            'documentation_url': '/api/docs',
            'capabilities': {
                'scan_management': {
                    'create_scans': True,
                    'list_scans': True,
                    'get_scan_details': True,
                    'cancel_scans': True,
                    'download_reports': True
                },
                'discovery': {
                    'list_generators': True,
                    'list_models': True,
                    'list_probe_categories': True,
                    'list_probes': True
                },
                'admin': {
                    'api_key_management': True,
                    'rate_limit_management': True,
                    'system_statistics': True
                }
            },
            'supported_generators': list(get_generators().keys()),
            'supported_probe_categories': list(get_probe_categories().keys()),
            'rate_limiting': {
                'enabled': True,
                'default_limits': {
                    'read_operations': '100/minute',
                    'write_operations': '50/minute',
                    'scan_creation': '10/minute'
                }
            },
            'authentication': {
                'methods': ['API Key'],
                'headers': ['Authorization: Bearer <token>', 'X-API-Key: <token>'],
                'permissions': ['read', 'write', 'admin']
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting API info: {str(e)}")
        return jsonify(ErrorResponse(
            error="info_retrieval_failed",
            message="Failed to retrieve API information"
        ).model_dump()), 500


@api_metadata.route('/health', methods=['GET'])
@rate_limit(limit=1000, window=60)  # High limit for health checks
def health_check():
    """API health check endpoint."""
    try:
        from datetime import datetime
        
        # Check various system components
        services = {}
        
        # Check Redis connection
        try:
            from api.core.rate_limiter import rate_limiter
            if rate_limiter.redis_client:
                rate_limiter.redis_client.ping()
                services['redis'] = 'healthy'
            else:
                services['redis'] = 'disabled'
        except Exception:
            services['redis'] = 'unhealthy'
        
        # Check database
        try:
            from api.core.database import db_manager
            db_info = db_manager.get_database_info()
            services['database'] = db_info['status']
            services['database_type'] = db_info['type']
            services['database_version'] = db_info['version']
        except Exception as e:
            services['database'] = 'unhealthy'
            services['database_error'] = str(e)
        
        # Check storage system
        try:
            from api.core.storage import storage_manager
            storage_info = storage_manager.health_check()
            services['storage'] = storage_info['status']
            services['storage_type'] = storage_info['type']
        except Exception as e:
            services['storage'] = 'unhealthy'
            services['storage_error'] = str(e)
        
        # Check job system
        try:
            get_jobs_data()
            services['job_system'] = 'healthy'
        except Exception:
            services['job_system'] = 'unhealthy'
        
        # Determine overall status
        status = 'healthy'
        if any(service == 'unhealthy' for service in services.values()):
            status = 'degraded'
        if all(service == 'unhealthy' for service in services.values()):
            status = 'unhealthy'
        
        response = HealthResponse(
            status=status,
            timestamp=str(datetime.now()),
            version='1.0.0',
            services=services
        )
        
        status_code = 200 if status == 'healthy' else 503
        return jsonify(response.model_dump()), status_code
        
    except Exception as e:
        current_app.logger.error(f"Error in health check: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': str(datetime.now())
        }), 503