import yaml
import os

def load_config():
    config_path = os.path.expanduser('~/.infrakit/config.yaml')
    with open(config_path) as f:
        return yaml.safe_load(f)