#!/usr/bin/env python3
"""
Import sanity test to catch relative import errors.
This test ensures all command modules can be imported without errors.
Run from the functions directory: python3 test_imports.py
"""
import sys
import ast
from pathlib import Path

def check_imports_are_absolute(filename):
    """Check that a Python file uses only absolute imports (no relative imports)."""
    with open(filename, 'r') as f:
        try:
            tree = ast.parse(f.read(), filename)
        except SyntaxError as e:
            return False, f'Syntax error: {e}'
    
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level > 0:  # relative import detected
                dots = "." * node.level
                module = node.module or ""
                return False, f'Relative import at line {node.lineno}: from {dots}{module}'
    
    return True, 'OK'

def main():
    """Main test function."""
    print("Testing import convention compliance...")
    print("=" * 60)
    
    # Check all command files
    commands_dir = Path(__file__).parent / "commands"
    db_dir = Path(__file__).parent / "db"
    
    files_to_check = []
    files_to_check.extend(commands_dir.glob("*.py"))
    files_to_check.extend(db_dir.glob("*.py"))
    
    # Filter out __init__.py files
    files_to_check = [f for f in files_to_check if f.name != "__init__.py"]
    
    all_passed = True
    for file_path in sorted(files_to_check):
        relative_path = file_path.relative_to(Path(__file__).parent)
        ok, msg = check_imports_are_absolute(file_path)
        
        status = "✓" if ok else "✗"
        print(f"{status} {relative_path}: {msg}")
        
        if not ok:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("✓ All imports follow absolute import convention!")
        return 0
    else:
        print("✗ Some files use relative imports. Please fix them.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
