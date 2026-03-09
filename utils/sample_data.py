"""
Sample data loader for SAP Confirmation Validator
Provides default example files for testing and demonstration
"""

import os
from pathlib import Path


def get_sample_files():
    """Get paths to sample files for demonstration"""
    current_dir = Path(__file__).parent.parent
    
    sample_files = {
        'eao_file': current_dir / 'data' / '-V90063_64-20260224103356.eao.suc',
        'xml_file': current_dir / 'data' / '20260225095318_-V90063_64_0224_01_20260225_095103.XML'
    }
    
    # Check if files exist
    available_files = {}
    for key, path in sample_files.items():
        if path.exists():
            available_files[key] = path
        else:
            print(f"Warning: Sample file not found: {path}")
    
    return available_files


def load_sample_file_content(file_path):
    """Load content from a sample file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error loading sample file {file_path}: {str(e)}")
        return None


def load_default_samples():
    """Load all available sample files"""
    sample_files = get_sample_files()
    loaded_data = {}
    
    for key, file_path in sample_files.items():
        content = load_sample_file_content(file_path)
        if content:
            loaded_data[key] = content
    
    return loaded_data
