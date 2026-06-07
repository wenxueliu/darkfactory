"""Shared pytest configuration for hooks/tests."""
import sys
from pathlib import Path

# Make the hooks/ directory importable for test files
HOOKS_DIR = Path(__file__).resolve().parent.parent
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))
