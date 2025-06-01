"""
pytest configuration for claude-code tests
"""
import sys
import os

# Add functions directory to path for imports
functions_dir = os.path.join(os.path.dirname(__file__), '..', 'functions')
sys.path.insert(0, functions_dir)