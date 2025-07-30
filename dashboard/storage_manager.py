"""
Storage manager compatibility module.

This module provides a simple wrapper around the StorageManager
to maintain compatibility with existing imports.
"""

from api.core.storage import StorageManager

def create_storage_manager():
    """Create and return a StorageManager instance."""
    return StorageManager()