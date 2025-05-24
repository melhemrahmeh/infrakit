#!/usr/bin/env python3
import argparse
import json
import logging
import os
import subprocess
import sys
from typing import Dict, Any

import psycopg2
import redis
import requests
import yaml
from requests.auth import HTTPBasicAuth

# Configuration
CONFIG_FILE = os.path.expanduser("~/.infrakit/config.yaml")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

class InfraKitCLI:
    def __init__(self):
        self.config = self.load_config()
        self.logger = self.setup_logging()
        self.db_conn = self.connect_postgresql()
        self.redis_client = self.connect_redis()
        
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(CONFIG_FILE) as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"Config file not found at {CONFIG_FILE}")
            sys.exit(1)
        except yaml.YAMLError as e:
            print(f"Error parsing config file: {e}")
            sys.exit(1)
    
    def setup_logging(self) -> logging.Logger:
        """Configure logging"""
        logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
        return logging.getLogger("infrakit")
    
    def connect_postgresql(self):
        """Connect to PostgreSQL database"""
        try:
            return psycopg2.connect(self.config["postgresql"]["url"])
        except Exception as e:
            self.logger.error(f"PostgreSQL connection failed: {e}")
            sys.exit(1)
    
    def connect_redis(self):
        """Connect to Redis"""
        try:
            return redis.Redis.from_url(self.config["redis"]["url"])
        except Exception as e:
            self.logger.error(f"Redis connection failed: {e}")
            sys.exit(1)
    
    def call_go_service(self, command: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Go service binary with JSON input/output"""
        try:
            input_json = json.dumps(args).encode()
            result = subprocess.run(
                [self.config["go_service"]["path"], command],
                input=input_json,
                capture_output=True,
                check=True
            )
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Go service failed: {e.stderr.decode()}")
            sys.exit(1)
    
    def onboard_application(self, args):
        """Onboard a new application"""
        self.logger.info(f"Starting onboarding for {args.name}")
        
        # Store in PostgreSQL
        self.store_application(args)
        
        # Call Go service for Helm operations
        helm_result = self.call_go_service("generate-helm", {
            "name": args.name,
            "chart": args.chart,
            "values": args.values_file,
            "output_dir": f"generated/{args.name}"
        })
        
        # Create ArgoCD application
        self.create_argocd_application(args, helm_result["manifest_path"])
        
        self.logger.info(f"Successfully onboarded {args.name}")
    
    def store_application(self, args):
        """Store application in PostgreSQL"""
        with self.db_conn.cursor() as cur:
            cur.execute("""
                INSERT INTO applications (name, cluster, namespace, helm_chart, git_repo, git_revision, git_path)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (name) DO UPDATE
                SET cluster = EXCLUDED.cluster,
                    namespace = EXCLUDED.namespace,
                    helm_chart = EXCLUDED.helm_chart,
                    git_repo = EXCLUDED.git_repo,
                    git_revision = EXCLUDED.git_revision,
                    git_path = EXCLUDED.git_path,
                    updated_at = NOW()
            """, (
                args.name, args.cluster, args.namespace, args.chart,
                args.repo, args.revision, args.path
            ))
            self.db_conn.commit()
    
    def create_argocd_application(self, args, manifest_path):
        """Create application in ArgoCD"""
        app_manifest = {
            "apiVersion": "argoproj.io/v1alpha1",
            "kind": "Application",
            "metadata": {
                "name": args.name,
                "namespace": self.config["argocd"]["namespace"]
            },
            "spec": {
                "project": "default",
                "source": {
                    "repoURL": args.repo,
                    "targetRevision": args.revision,
                    "path": args.path
                },
                "destination": {
                    "server": f"https://kubernetes.default.svc",
                    "namespace": args.namespace
                },
                "syncPolicy": {
                    "automated": {
                        "prune": True,
                        "selfHeal": True
                    }
                }
            }
        }
        
        auth = HTTPBasicAuth(
            self.config["argocd"]["username"],
            self.config["argocd"]["password"]
        )
        
        response = requests.post(
            f"{self.config['argocd']['apiUrl']}/api/v1/applications",
            json=app_manifest,
            auth=auth
        )
        
        if response.status_code != 200:
            self.logger.error(f"ArgoCD API error: {response.text}")
            sys.exit(1)
    
    def sync_application(self, args):
        """Sync an ArgoCD application"""
        auth = HTTPBasicAuth(
            self.config["argocd"]["username"],
            self.config["argocd"]["password"]
        )
        
        response = requests.post(
            f"{self.config['argocd']['apiUrl']}/api/v1/applications/{args.name}/sync",
            json={},
            auth=auth
        )
        
        if response.status_code != 200:
            self.logger.error(f"ArgoCD sync failed: {response.text}")
            sys.exit(1)
        
        self.logger.info(f"Sync triggered for {args.name}")
    
    def get_application_status(self, args):
        """Get application status"""
        auth = HTTPBasicAuth(
            self.config["argocd"]["username"],
            self.config["argocd"]["password"]
        )
        
        response = requests.get(
            f"{self.config['argocd']['apiUrl']}/api/v1/applications/{args.name}",
            auth=auth
        )
        
        if response.status_code != 200:
            self.logger.error(f"ArgoCD status check failed: {response.text}")
            sys.exit(1)
        
        status = response.json()
        print(f"Status for {args.name}:")
        print(f"  Health: {status['status']['health']['status']}")
        print(f"  Sync: {status['status']['sync']['status']}")
        print(f"  Revision: {status['status']['sync']['revision']}")

def main():
    cli = InfraKitCLI()
    
    parser = argparse.ArgumentParser(description="InfraKit - Multi-Cluster GitOps Automation")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Onboard command
    onboard_parser = subparsers.add_parser("onboard", help="Onboard a new application")
    onboard_parser.add_argument("--name", required=True, help="Application name")
    onboard_parser.add_argument("--cluster", required=True, help="Target cluster")
    onboard_parser.add_argument("--namespace", required=True, help="Target namespace")
    onboard_parser.add_argument("--chart", required=True, help="Helm chart URL")
    onboard_parser.add_argument("--values-file", help="Helm values file")
    onboard_parser.add_argument("--repo", required=True, help="Git repository URL")
    onboard_parser.add_argument("--revision", default="main", help="Git revision")
    onboard_parser.add_argument("--path", required=True, help="Path in repository")
    onboard_parser.set_defaults(func=cli.onboard_application)
    
    # Sync command
    sync_parser = subparsers.add_parser("sync", help="Sync an application")
    sync_parser.add_argument("name", help="Application name")
    sync_parser.set_defaults(func=cli.sync_application)
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Check application status")
    status_parser.add_argument("name", help="Application name")
    status_parser.set_defaults(func=cli.get_application_status)
    
    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()