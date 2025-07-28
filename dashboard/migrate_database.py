#!/usr/bin/env python3
"""
Database migration script to add missing columns.
"""

import sqlite3
import os
import sys

def migrate_database(db_path):
    """Add missing columns to existing database."""
    print(f"🔄 Migrating database: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check current schema
        cursor.execute("PRAGMA table_info(api_keys)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"📋 Current columns: {columns}")
        
        # Add user_id column if missing
        if 'user_id' not in columns:
            print("➕ Adding user_id column...")
            cursor.execute("ALTER TABLE api_keys ADD COLUMN user_id TEXT")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id)")
            print("✅ Added user_id column and index")
        else:
            print("✅ user_id column already exists")
        
        conn.commit()
        conn.close()
        
        print("🎉 Database migration completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == '__main__':
    db_path = 'data/api_keys.db'
    success = migrate_database(db_path)
    sys.exit(0 if success else 1)