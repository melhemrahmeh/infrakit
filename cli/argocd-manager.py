import requests
from requests.auth import HTTPBasicAuth

class ArgoCDManager:
    def __init__(self, config):
        self.api_url = config['apiUrl']
        self.auth = HTTPBasicAuth(config['username'], config['password'])
    
    def create_application(self, name, cluster):
        app_manifest = {
            "apiVersion": "argoproj.io/v1alpha1",
            "kind": "Application",
            "metadata": {"name": name},
            "spec": {
                "destination": {
                    "server": f"https://{cluster}.example.com",
                    "namespace": "default"
                }
            }
        }
        
        response = requests.post(
            f"{self.api_url}/api/v1/applications",
            json=app_manifest,
            auth=self.auth
        )
        response.raise_for_status()
        return response.json()