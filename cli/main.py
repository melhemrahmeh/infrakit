#!/usr/bin/env python3
import argparse
import logging
from config.settings import load_config
from db_manager import DBManager
from argocd_manager import ArgoCDManager
from redis_manager import RedisManager  # Added Redis import

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    config = load_config()
    db = DBManager(config['postgresql']['url'])
    argocd = ArgoCDManager(config['argocd'])
    redis = RedisManager(config['redis']['url'])  # Initialize Redis
    
    parser = argparse.ArgumentParser(description='InfraKit CLI')
    subparsers = parser.add_subparsers(dest='command', required=True)
    
    # Onboard command
    onboard_parser = subparsers.add_parser('onboard')
    onboard_parser.add_argument('--name', required=True)
    onboard_parser.add_argument('--cluster', required=True)
    onboard_parser.add_argument('--chart', required=True)
    
    # Status command
    status_parser = subparsers.add_parser('status')
    status_parser.add_argument('name')
    
    args = parser.parse_args()
    
    if args.command == 'onboard':
        if not redis.acquire_lock(f"onboard:{args.name}"):
            logger.error("Operation already in progress")
            return
        
        try:
            logger.info(f"Onboarding {args.name}")
            db.create_application(args.name, args.cluster, args.chart)
            redis.cache_application_state(args.name, {
                "status": "provisioning",
                "cluster": args.cluster
            })
            argocd.create_application(args.name, args.cluster)
            redis.cache_application_state(args.name, {
                "status": "active",
                "cluster": args.cluster
            })
        finally:
            redis.release_lock(f"onboard:{args.name}")
    
    elif args.command == 'status':
        if state := redis.get_cached_state(args.name):
            logger.info(f"Current state: {state}")
        else:
            logger.info("No cached state available")

if __name__ == '__main__':
    main()