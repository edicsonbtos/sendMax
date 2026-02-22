#!/usr/bin/env python3
"""
Guardrail script to detect Mojibake in the codebase.
Patterns checked: â, Ã, ð, ï, etc.
"""
import os
import sys

# Patterns to detect (common Mojibake signatures in UTF-8 displayed as Latin-1)
PATTERNS = [
    b'\xc3\x83', # Ã
    b'\xc3\xa2', # â
    b'\xc3\xb0', # ð
    b'\xc3\xaf', # ï
    b'\xc3\x82', # Â
]

# Files/dirs to exclude
EXCLUDE_DIRS = ['.git', '__pycache__', 'node_modules', '.venv', 'venv', 'alembic']
EXCLUDE_FILES = ['check_mojibake.py', 'bot_persistence.pickle']

def scan_file(filepath):
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
            for p in PATTERNS:
                if p in content:
                    return True, p
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    return False, None

def main():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    errors = 0

    print(f"Scanning for Mojibake in {root_dir}...")

    for root, dirs, files in os.walk(root_dir):
        # Prune excluded dirs
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for file in files:
            if file in EXCLUDE_FILES:
                continue
            if not file.endswith(('.py', '.js', '.ts', '.tsx', '.html', '.txt', '.md')):
                continue

            filepath = os.path.join(root, file)
            found, pattern = scan_file(filepath)
            if found:
                print(f"MOJIBAKE DETECTED: {filepath} (pattern {pattern})")
                errors += 1

    if errors > 0:
        print(f"\nTotal files with Mojibake: {errors}")
        sys.exit(1)
    else:
        print("\nClean! No Mojibake patterns found.")
        sys.exit(0)

if __name__ == "__main__":
    main()
