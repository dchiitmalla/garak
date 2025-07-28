"""
Admin endpoints for API key management in Garak Dashboard.

This module provides administrative endpoints for creating, listing,
and managing API keys for the public API.
"""

from flask import Blueprint, request, jsonify, current_app, g
from pydantic import ValidationError

from api.core.auth import api_key_manager, admin_required, api_key_required
from api.core.rate_limiter import rate_limit, get_rate_limit_status
from api.core.models import (
    CreateAPIKeyRequest, APIKeyResponse, APIKeyInfo, ErrorResponse,
    RateLimitInfo
)
from api.core.utils import validate_json_request, create_error_handler, get_jobs_data

# Blueprint for admin API endpoints
api_admin = Blueprint('api_admin', __name__, url_prefix='/api/v1/admin')


# validate_json_request is now imported from api.core.utils


@api_admin.errorhandler(Exception)
def handle_admin_error(error):
    """Global error handler for admin API."""
    return create_error_handler("Admin API")(error)


# API Key Management Endpoints

@api_admin.route('/api-keys', methods=['POST'])
@admin_required
@rate_limit(limit=10, window=60)  # 10 key creations per minute
@validate_json_request(CreateAPIKeyRequest)
def create_api_key(request_data: CreateAPIKeyRequest):
    """Create a new API key."""
    try:
        # Convert permissions to comma-separated string
        permissions_str = ','.join([perm.value for perm in request_data.permissions])
        
        # Generate the API key
        api_key, key_metadata = api_key_manager.generate_api_key(
            name=request_data.name,
            description=request_data.description,
            permissions=permissions_str,
            rate_limit=request_data.rate_limit,
            expires_days=request_data.expires_days
        )
        
        # Convert metadata to Pydantic model
        key_info = APIKeyInfo(
            id=key_metadata['id'],
            key_prefix=key_metadata['key_prefix'],
            name=key_metadata['name'],
            description=key_metadata['description'],
            permissions=key_metadata['permissions'],
            rate_limit=key_metadata['rate_limit'],
            usage_count=0,
            created_at=key_metadata['created_at'],
            last_used=None,
            expires_at=key_metadata['expires_at'],
            is_active=True
        )
        
        response = APIKeyResponse(
            api_key=api_key,
            key_info=key_info
        )
        
        current_app.logger.info(
            f"Created API key '{request_data.name}' with permissions {request_data.permissions} - "
            f"Admin: {g.api_key_info['key_prefix']} ({g.api_key_info['name']})"
        )
        
        return jsonify(response.model_dump()), 201
        
    except Exception as e:
        current_app.logger.error(f"Error creating API key: {str(e)}")
        return jsonify(ErrorResponse(
            error="key_creation_failed",
            message=f"Failed to create API key: {str(e)}"
        ).model_dump()), 500


@api_admin.route('/api-keys', methods=['GET'])
@admin_required
@rate_limit(limit=100, window=60)
def list_api_keys():
    """List all API keys (without the actual key values)."""
    try:
        keys_data = api_key_manager.list_api_keys()
        
        # Convert to Pydantic models
        api_keys = []
        for key_data in keys_data:
            api_key_info = APIKeyInfo(
                id=key_data['id'],
                key_prefix=key_data['key_prefix'],
                name=key_data['name'],
                description=key_data['description'],
                permissions=key_data['permissions'],
                rate_limit=key_data['rate_limit'],
                usage_count=key_data['usage_count'],
                created_at=key_data['created_at'],
                last_used=key_data['last_used'],
                expires_at=key_data['expires_at'],
                is_active=key_data['is_active']
            )
            api_keys.append(api_key_info)
        
        return jsonify({
            'api_keys': [key.model_dump() for key in api_keys],
            'total': len(api_keys)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error listing API keys: {str(e)}")
        return jsonify(ErrorResponse(
            error="key_list_failed",
            message="Failed to list API keys"
        ).model_dump()), 500


@api_admin.route('/api-keys/<int:key_id>', methods=['GET'])
@admin_required
@rate_limit(limit=200, window=60)
def get_api_key(key_id: int):
    """Get detailed information about a specific API key."""
    try:
        keys_data = api_key_manager.list_api_keys()
        
        # Find the key
        key_data = None
        for key in keys_data:
            if key['id'] == key_id:
                key_data = key
                break
        
        if not key_data:
            return jsonify(ErrorResponse(
                error="key_not_found",
                message=f"API key with ID {key_id} not found"
            ).model_dump()), 404
        
        api_key_info = APIKeyInfo(
            id=key_data['id'],
            key_prefix=key_data['key_prefix'],
            name=key_data['name'],
            description=key_data['description'],
            permissions=key_data['permissions'],
            rate_limit=key_data['rate_limit'],
            usage_count=key_data['usage_count'],
            created_at=key_data['created_at'],
            last_used=key_data['last_used'],
            expires_at=key_data['expires_at'],
            is_active=key_data['is_active']
        )
        
        return jsonify(api_key_info.model_dump())
        
    except Exception as e:
        current_app.logger.error(f"Error getting API key {key_id}: {str(e)}")
        return jsonify(ErrorResponse(
            error="key_retrieval_failed",
            message="Failed to retrieve API key information"
        ).model_dump()), 500


@api_admin.route('/api-keys/<int:key_id>/revoke', methods=['POST'])
@admin_required
@rate_limit(limit=50, window=60)
def revoke_api_key(key_id: int):
    """Revoke an API key (deactivate it)."""
    try:
        success = api_key_manager.revoke_api_key(key_id)
        
        if not success:
            return jsonify(ErrorResponse(
                error="key_not_found",
                message=f"API key with ID {key_id} not found"
            ).model_dump()), 404
        
        current_app.logger.info(
            f"Revoked API key ID {key_id} - "
            f"Admin: {g.api_key_info['key_prefix']} ({g.api_key_info['name']})"
        )
        
        return jsonify({
            'message': f'API key {key_id} has been revoked',
            'key_id': key_id,
            'is_active': False
        })
        
    except Exception as e:
        current_app.logger.error(f"Error revoking API key {key_id}: {str(e)}")
        return jsonify(ErrorResponse(
            error="key_revocation_failed",
            message="Failed to revoke API key"
        ).model_dump()), 500


@api_admin.route('/api-keys/<int:key_id>', methods=['DELETE'])
@admin_required
@rate_limit(limit=20, window=60)
def delete_api_key(key_id: int):
    """Permanently delete an API key."""
    try:
        success = api_key_manager.delete_api_key(key_id)
        
        if not success:
            return jsonify(ErrorResponse(
                error="key_not_found",
                message=f"API key with ID {key_id} not found"
            ).model_dump()), 404
        
        current_app.logger.info(
            f"Deleted API key ID {key_id} - "
            f"Admin: {g.api_key_info['key_prefix']} ({g.api_key_info['name']})"
        )
        
        return jsonify({
            'message': f'API key {key_id} has been permanently deleted',
            'key_id': key_id
        })
        
    except Exception as e:
        current_app.logger.error(f"Error deleting API key {key_id}: {str(e)}")
        return jsonify(ErrorResponse(
            error="key_deletion_failed",
            message="Failed to delete API key"
        ).model_dump()), 500


# Rate Limiting Management

@api_admin.route('/api-keys/<int:key_id>/rate-limit', methods=['GET'])
@admin_required
@rate_limit(limit=100, window=60)
def get_api_key_rate_limit(key_id: int):
    """Get current rate limiting status for an API key."""
    try:
        # First verify the key exists
        keys_data = api_key_manager.list_api_keys()
        key_data = None
        for key in keys_data:
            if key['id'] == key_id:
                key_data = key
                break
        
        if not key_data:
            return jsonify(ErrorResponse(
                error="key_not_found",
                message=f"API key with ID {key_id} not found"
            ).model_dump()), 404
        
        # Get rate limit status
        rate_status = get_rate_limit_status(key_data)
        
        return jsonify(rate_status)
        
    except Exception as e:
        current_app.logger.error(f"Error getting rate limit for key {key_id}: {str(e)}")
        return jsonify(ErrorResponse(
            error="rate_limit_retrieval_failed",
            message="Failed to retrieve rate limit information"
        ).model_dump()), 500


# System Status and Statistics

@api_admin.route('/stats', methods=['GET'])
@admin_required
@rate_limit(limit=50, window=60)
def get_system_stats():
    """Get system statistics and API usage metrics."""
    try:
        # Get API key statistics
        keys_data = api_key_manager.list_api_keys()
        
        total_keys = len(keys_data)
        active_keys = len([k for k in keys_data if k['is_active']])
        total_requests = sum(k['usage_count'] for k in keys_data)
        
        # Get scan statistics
        jobs_data = get_jobs_data()
        
        total_scans = len(jobs_data)
        api_scans = len([j for j in jobs_data.values() if j.get('created_by_api')])
        running_scans = len([j for j in jobs_data.values() if j.get('status') in ['pending', 'running']])
        completed_scans = len([j for j in jobs_data.values() if j.get('status') == 'completed'])
        failed_scans = len([j for j in jobs_data.values() if j.get('status') == 'failed'])
        
        return jsonify({
            'api_keys': {
                'total': total_keys,
                'active': active_keys,
                'total_requests': total_requests
            },
            'scans': {
                'total': total_scans,
                'api_created': api_scans,
                'running': running_scans,
                'completed': completed_scans,
                'failed': failed_scans
            },
            'system': {
                'redis_connected': hasattr(g, 'rate_limiter') and g.rate_limiter.redis_client is not None
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting system stats: {str(e)}")
        return jsonify(ErrorResponse(
            error="stats_retrieval_failed",
            message="Failed to retrieve system statistics"
        ).model_dump()), 500


# Bootstrap/Initial Setup

@api_admin.route('/bootstrap', methods=['POST'])
def bootstrap_admin():
    """Create the initial admin API key for system setup."""
    try:
        # Check if any admin keys already exist
        keys_data = api_key_manager.list_api_keys()
        admin_keys = [k for k in keys_data if 'admin' in k['permissions']]
        
        if admin_keys:
            return jsonify(ErrorResponse(
                error="admin_exists",
                message="Admin API key already exists. Use existing admin key to create more keys."
            ).model_dump()), 400
        
        # Create the initial admin key
        api_key, key_metadata = api_key_manager.generate_api_key(
            name="Initial Admin Key",
            description="Bootstrap admin key for system setup",
            permissions="read,write,admin",
            rate_limit=1000,  # Higher limit for admin
            expires_days=None  # No expiration
        )
        
        key_info = APIKeyInfo(
            id=key_metadata['id'],
            key_prefix=key_metadata['key_prefix'],
            name=key_metadata['name'],
            description=key_metadata['description'],
            permissions=key_metadata['permissions'],
            rate_limit=key_metadata['rate_limit'],
            usage_count=0,
            created_at=key_metadata['created_at'],
            last_used=None,
            expires_at=key_metadata['expires_at'],
            is_active=True
        )
        
        response = APIKeyResponse(
            api_key=api_key,
            key_info=key_info
        )
        
        current_app.logger.info("Created bootstrap admin API key")
        
        return jsonify({
            **response.model_dump(),
            'message': 'Bootstrap admin key created successfully. Store this key securely - it will not be shown again.',
            'next_steps': [
                'Store the API key in a secure location',
                'Use this key to create additional API keys with appropriate permissions',
                'Consider setting up rate limiting and monitoring'
            ]
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error creating bootstrap admin key: {str(e)}")
        return jsonify(ErrorResponse(
            error="bootstrap_failed",
            message=f"Failed to create bootstrap admin key: {str(e)}"
        ).model_dump()), 500