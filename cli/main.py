#!/usr/bin/env python3
import argparse
import json
import logging
import subprocess
import sys
from typing import Dict, Optional

from redis_manager import RedisManager
from argocd_manager import ArgoCDManager
from db_manager import DBManager
from config.settings import load_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('infrakit.log')
    ]
)
logger = logging.getLogger(__name__)

class InfraKitCLI:
    def __init__(self):
        self.config = self._load_config()
        self.redis = RedisManager(self.config['redis']['url'])
        self.db = DBManager(self.config['postgresql']['url'])
        self.argocd = ArgoCDManager(self.config['argocd'])
        self.go_service_path = self.config['go_service']['path']

    def _load_config(self) -> Dict:
        """Load and validate configuration"""
        try:
            config = load_config()
            required_sections = ['redis', 'postgresql', 'argocd', 'go_service']
            if not all(section in config for section in required_sections):
                raise ValueError("Missing required config sections")
            return config
        except Exception as e:
            logger.error(f"Configuration error: {e}")
            sys.exit(1)

    def _call_go_service(self, command: str, payload: Dict) -> Dict:
        """Execute Go service with JSON input/output"""
        try:
            result = subprocess.run(
                [self.go_service_path, command],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                check=True
            )
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            logger.error(f"Go service failed: {e.stderr}")
            raise
        except json.JSONDecodeError:
            logger.error("Invalid JSON response from Go service")
            raise

    def onboard(self, args) -> None:
        """Onboard a new application"""
        lock_key = f"onboard:{args.name}"
        
        if not self.redis.acquire_lock(lock_key):
            logger.error(f"Onboarding already in progress for {args.name}")
            return

        try:
            logger.info(f"Starting onboarding for {args.name}")
            
            # Generate Helm templates
            helm_result = self._call_go_service("generate-helm", {
                "name": args.name,
                "chart": args.chart,
                "values": args.values
            })
            
            # Validate Kubernetes manifests
            validation = self._call_go_service("validate-k8s", {
                "manifest": helm_result['manifest'],
                "kubeconfig": args.kubeconfig
            })
            
            if not validation.get('valid'):
                raise ValueError(f"Manifest validation failed: {validation.get('error')}")
            
            # Store in database
            self.db.create_application(
                name=args.name,
                cluster=args.cluster,
                namespace=args.namespace,
                chart=args.chart,
                repo=args.repo
            )
            
            # Create ArgoCD application
            self.argocd.create_application(
                name=args.name,
                cluster=args.cluster,
                repo=args.repo,
                path=args.path,
                revision=args.revision
            )
            
            # Update cache
            self.redis.cache_application_state(args.name, {
                "status": "active",
                "cluster": args.cluster,
                "last_operation": "onboard"
            })
            
            logger.info(f"Successfully onboarded {args.name}")
            
        except Exception as e:
            self.redis.cache_application_state(args.name, {
                "status": "failed",
                "error": str(e)
            })
            logger.error(f"Onboarding failed: {e}")
            raise
        finally:
            self.redis.release_lock(lock_key)

    def status(self, name: str) -> Optional[Dict]:
        """Check application status"""
        if cached := self.redis.get_cached_state(name):
            logger.info(f"Cached status: {cached}")
            return cached
        
        logger.info("No cached status, checking database...")
        return self.db.get_application(name)

    def sync(self, name: str) -> None:
        """Trigger application sync"""
        if not self.redis.acquire_lock(f"sync:{name}", ttl=60):
            raise RuntimeError(f"Sync already in progress for {name}")
        
        try:
            self.argocd.sync_application(name)
            self.redis.cache_application_state(name, {
                "status": "syncing",
                "last_sync": "pending"
            })
            logger.info(f"Sync triggered for {name}")
        finally:
            self.redis.release_lock(f"sync:{name}")

def main():
    cli = InfraKitCLI()
    
    parser = argparse.ArgumentParser(description="InfraKit - GitOps Automation Tool")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Onboard command
    onboard_parser = subparsers.add_parser("onboard", help="Onboard a new application")
    onboard_parser.add_argument("--name", required=True, help="Application name")
    onboard_parser.add_argument("--cluster", required=True, help="Target cluster")
    onboard_parser.add_argument("--namespace", default="default", help="Kubernetes namespace")
    onboard_parser.add_argument("--chart", required=True, help="Helm chart reference")
    onboard_parser.add_argument("--repo", required=True, help="Git repository URL")
    onboard_parser.add_argument("--path", default=".", help="Path in repository")
    onboard_parser.add_argument("--revision", default="main", help="Git revision")
    onboard_parser.add_argument("--values", help="Helm values JSON string")
    onboard_parser.add_argument("--kubeconfig", help="Custom kubeconfig path")
    onboard_parser.set_defaults(func=cli.onboard)
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Check application status")
    status_parser.add_argument("name", help="Application name")
    status_parser.set_defaults(func=cli.status)
    
    # Sync command
    sync_parser = subparsers.add_parser("sync", help="Sync application")
    sync_parser.add_argument("name", help="Application name")
    sync_parser.set_defaults(func=cli.sync)
    
    args = parser.parse_args()
    
    try:
        result = args.func(args) if hasattr(args, 'func') else None
        if result:
            print(json.dumps(result, indent=2))
    except Exception as e:
        logger.error(f"Command failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()