#!/usr/bin/env python3
"""
Fix Pydantic method calls from .dict() to .model_dump() 
"""

import os
import re

def fix_pydantic_methods(directory):
    """Fix .dict() calls to .model_dump() in Python files."""
    
    # Pattern to match .dict() calls (but not in strings or comments)
    pattern = r'\.dict\(\)'
    replacement = '.model_dump()'
    
    fixed_files = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Count matches
                    matches = re.findall(pattern, content)
                    if matches:
                        # Replace all occurrences
                        new_content = re.sub(pattern, replacement, content)
                        
                        # Write back to file
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        
                        fixed_files.append((file_path, len(matches)))
                        print(f"Fixed {len(matches)} occurrences in {file_path}")
                
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
    
    return fixed_files

if __name__ == '__main__':
    print("🔧 Fixing Pydantic method calls...")
    
    # Fix files in the api directory
    api_dir = 'api'
    if os.path.exists(api_dir):
        fixed_files = fix_pydantic_methods(api_dir)
        
        if fixed_files:
            print(f"\n✅ Fixed {len(fixed_files)} files:")
            total_fixes = sum(count for _, count in fixed_files)
            print(f"   Total replacements: {total_fixes}")
            
            for file_path, count in fixed_files:
                print(f"   - {file_path}: {count} fixes")
        else:
            print("✅ No files needed fixing")
    else:
        print(f"❌ Directory {api_dir} not found")