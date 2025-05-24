#!/usr/bin/env python3
import argparse
import logging
from config.settings import load_config
from db_manager import DBManager
from argocd_manager import ArgoCDManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    config = load_config()
    db = DBManager(config['postgresql']['url'])
    argocd = ArgoCDManager(config['argocd'])
    
    parser = argparse.ArgumentParser(description='InfraKit CLI')
    subparsers = parser.add_subparsers(dest='command', required=True)
    
    # Onboard command
    onboard_parser = subparsers.add_parser('onboard')
    onboard_parser.add_argument('--name', required=True)
    onboard_parser.add_argument('--cluster', required=True)
    onboard_parser.add_argument('--chart', required=True)
    
    args = parser.parse_args()
    
    if args.command == 'onboard':
        logger.info(f"Onboarding {args.name}")
        db.create_application(args.name, args.cluster, args.chart)
        argocd.create_application(args.name, args.cluster)

if __name__ == '__main__':
    main()