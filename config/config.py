import json
import os

def load():
    """Load configuration from settings.json file with environment variable overrides."""
    config_path = os.path.join(os.path.dirname(__file__), 'settings.json')
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Override with environment variables if they exist
    if 'OPENAI_API_KEY' in os.environ:
        config['openai_api_key'] = os.environ['OPENAI_API_KEY']
    if 'VECTOR_STORE_PATH' in os.environ:
        config['vector_store_path'] = os.environ['VECTOR_STORE_PATH']
    
    return config

def get_setting(key, default=None):
    """Get a specific setting with optional default value."""
    config = load()
    return config.get(key, default)

def save_setting(key, value):
    """Save a specific setting to the config file."""
    config = load()
    config[key] = value
    config_path = os.path.join(os.path.dirname(__file__), 'settings.json')
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)