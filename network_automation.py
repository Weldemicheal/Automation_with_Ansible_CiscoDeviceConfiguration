# !/usr/bin/env python3
"""
Network Automation Script for Cisco Configuration
With complete error handling and reporting
"""

import os
import sys
import time
import logging
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
import json
import yaml

# Configure logging
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f"automation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


class NetworkAutomation:
    """Main automation class"""

    def __init__(self, playbook_path="configure_network.yml",
                 inventory_path="inventory.yml", dry_run=False):
        self.playbook_path = playbook_path
        self.inventory_path = inventory_path
        self.dry_run = dry_run
        self.start_time = datetime.now()
        self.results = {
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'total': 0
        }

    def print_banner(self):
        """Print automation banner"""
        print(f"\n{Colors.CYAN}{'=' * 60}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BLUE}  Network Automation Suite v2.0{Colors.RESET}")
        print(f"{Colors.CYAN}{'=' * 60}{Colors.RESET}")
        print(f"  Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Playbook: {self.playbook_path}")
        print(f"  Inventory: {self.inventory_path}")
        print(f"  Mode: {'DRY RUN' if self.dry_run else 'DEPLOY'}")
        print(f"{Colors.CYAN}{'=' * 60}{Colors.RESET}\n")

    def check_prerequisites(self):
        """Check if all prerequisites are met"""
        logger.info("Checking prerequisites...")
        checks_passed = True

        # Check if ansible is installed
        try:
            subprocess.run(['ansible', '--version'],
                           capture_output=True, check=True)
            logger.info("✅ Ansible is installed")
        except FileNotFoundError:
            logger.error("❌ Ansible not found. Please install Ansible.")
            checks_passed = False

        # Check if python packages are installed
        try:
            import yaml
            logger.info("✅ PyYAML is installed")
        except ImportError:
            logger.error("❌ PyYAML not installed. Run: pip install pyyaml")
            checks_passed = False

        # Check if playbook exists
        if not Path(self.playbook_path).exists():
            logger.error(f"❌ Playbook not found: {self.playbook_path}")
            checks_passed = False
        else:
            logger.info(f"✅ Playbook found: {self.playbook_path}")

        # Check if inventory exists
        if not Path(self.inventory_path).exists():
            logger.error(f"❌ Inventory not found: {self.inventory_path}")
            checks_passed = False
        else:
            logger.info(f"✅ Inventory found: {self.inventory_path}")

        return checks_passed

    def run_playbook(self):
        """Execute the Ansible playbook"""
        logger.info("Starting playbook execution...")

        # Build command
        cmd = ['ansible-playbook', self.playbook_path, '-i', self.inventory_path]

        if self.dry_run:
            cmd.append('--check')
            cmd.append('--diff')

        # Add verbosity
        cmd.append('-v')

        # Execute
        try:
            logger.info(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)

            # Log output
            if result.stdout:
                logger.info("Playbook output:")
                for line in result.stdout.split('\n'):
                    logger.info(f"  {line}")

            if result.stderr:
                logger.warning("Playbook stderr:")
                for line in result.stderr.split('\n'):
                    logger.warning(f"  {line}")

            # Parse results
            if result.returncode == 0:
                logger.info("✅ Playbook executed successfully")
                return True
            else:
                logger.error(f"❌ Playbook failed with return code: {result.returncode}")
                return False

        except Exception as e:
            logger.error(f"Error executing playbook: {str(e)}")
            return False

    def validate_results(self):
        """Validate the configuration after deployment"""
        logger.info("Validating configuration...")

        # Run validation script
        try:
            result = subprocess.run(['python3', 'validate_config.py'],
                                    capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("✅ Validation passed")
                return True
            else:
                logger.error("❌ Validation failed")
                return False
        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            return False

    def run(self):
        """Main execution flow"""
        self.print_banner()

        # Check prerequisites
        if not self.check_prerequisites():
            logger.error("Prerequisites check failed. Exiting.")
            return 1

        # Run playbook
        success = self.run_playbook()

        if not success:
            logger.error("Playbook execution failed.")
            return 1

        # Validate if not dry run
        if not self.dry_run:
            if not self.validate_results():
                logger.warning("Validation failed. Check logs.")
                return 1

        # Print summary
        elapsed = datetime.now() - self.start_time
        print(f"\n{Colors.GREEN}{'=' * 60}{Colors.RESET}")
        print(f"{Colors.BOLD}  AUTOMATION COMPLETED{Colors.RESET}")
        print(f"  Status: {'✅ SUCCESS' if success else '❌ FAILED'}")
        print(f"  Duration: {elapsed.total_seconds():.2f} seconds")
        print(f"{Colors.GREEN}{'=' * 60}{Colors.RESET}\n")

        return 0


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Network Automation with Ansible',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python network_automation.py                    # Run automation
  python network_automation.py --dry-run          # Dry run
  python network_automation.py --playbook custom.yml  # Custom playbook
  python network_automation.py --inventory custom.yml # Custom inventory
        """
    )
    parser.add_argument(
        '--playbook', '-p',
        default='configure_network.yml',
        help='Path to Ansible playbook (default: configure_network.yml)'
    )
    parser.add_argument(
        '--inventory', '-i',
        default='inventory.yml',
        help='Path to inventory file (default: inventory.yml)'
    )
    parser.add_argument(
        '--dry-run', '-d',
        action='store_true',
        help='Perform dry run (check mode)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Run automation
    automation = NetworkAutomation(
        playbook_path=args.playbook,
        inventory_path=args.inventory,
        dry_run=args.dry_run
    )

    sys.exit(automation.run())


if __name__ == '__main__':
    main()