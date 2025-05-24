import yaml
import os

def load_config():
    config_path = os.environ.get('INFRIKIT_CONFIG', os.path.expanduser('~/.infrakit/config.yaml'))
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    try:
        with open(config_path) as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise RuntimeError(f"Failed to parse YAML config: {e}")