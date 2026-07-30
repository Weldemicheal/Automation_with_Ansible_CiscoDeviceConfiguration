#!/usr/bin/env python3
"""
Network Automation Script for Cisco Configuration
Windows-compatible version - Fixed
"""

import os
import sys
import time
import logging
import argparse
import subprocess
import platform
from datetime import datetime
from pathlib import Path

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


class NetworkAutomation:
    """Main automation class - Windows compatible"""

    def __init__(self, playbook_path="configure_network.yml",
                 inventory_path="inventory.yml", dry_run=False):
        self.playbook_path = playbook_path
        self.inventory_path = inventory_path
        self.dry_run = dry_run
        self.start_time = datetime.now()
        self.is_windows = platform.system() == 'Windows'

    def get_playbook_cmd(self):
        """Get the correct ansible-playbook command for the OS"""
        if self.is_windows:
            return ['python', '-m', 'ansible.playbook']
        return ['ansible-playbook']

    def print_banner(self):
        """Print automation banner"""
        print(f"\n{'=' * 60}")
        print(f"  Network Automation Suite v2.0")
        print(f"  OS: {platform.system()} {platform.release()}")
        print(f"  Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Playbook: {self.playbook_path}")
        print(f"  Inventory: {self.inventory_path}")
        print(f"  Mode: {'DRY RUN' if self.dry_run else 'DEPLOY'}")
        print(f"{'=' * 60}\n")

    def check_prerequisites(self):
        """Check if all prerequisites are met"""
        logger.info("Checking prerequisites...")
        checks_passed = True
        ansible_found = False

        # Try different methods to find ansible
        methods = [
            # Method 1: Direct ansible command
            (['ansible', '--version'], 'direct command'),
            # Method 2: Python module with cli.adhoc
            (['python', '-m', 'ansible.cli.adhoc', '--version'], 'python module'),
            # Method 3: ansible-playbook
            (['ansible-playbook', '--version'], 'ansible-playbook'),
            # Method 4: Python module for playbook
            (['python', '-m', 'ansible.playbook', '--version'], 'python playbook module'),
        ]

        for cmd, method_name in methods:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    version_line = result.stdout.split('\n')[0] if result.stdout else "Version found"
                    if "Error" not in version_line and "error" not in version_line.lower():
                        logger.info(f"✅ Ansible is installed ({method_name})")
                        logger.info(f"   {version_line}")
                        ansible_found = True
                        break
            except:
                continue

        # Method 5: Try importing ansible
        if not ansible_found:
            try:
                import ansible
                logger.info(f"✅ Ansible module found (imported successfully)")
                ansible_found = True
            except ImportError:
                pass

        if not ansible_found:
            logger.error("❌ Ansible not found. Please install Ansible.")
            logger.info("   Installation: python -m pip install ansible")
            checks_passed = False

        # Check if python packages are installed
        try:
            import yaml
            logger.info("✅ PyYAML is installed")
        except ImportError:
            logger.error("❌ PyYAML not installed. Run: python -m pip install pyyaml")
            checks_passed = False

        # Check if jinja2 is installed
        try:
            import jinja2
            logger.info("✅ Jinja2 is installed")
        except ImportError:
            logger.warning("⚠️ Jinja2 not installed (optional)")

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

        if not checks_passed:
            logger.info("\n" + "=" * 60)
            logger.info("TROUBLESHOOTING GUIDE")
            logger.info("=" * 60)
            logger.info("To install Ansible:")
            logger.info("  python -m pip install ansible")
            logger.info("")
            logger.info("Or install WSL (recommended for Windows):")
            logger.info("  wsl --install")
            logger.info("  wsl sudo apt install ansible")
            logger.info("=" * 60)
        else:
            logger.info("✅ All prerequisites met!")

        return checks_passed

    def run_playbook(self):
        """Execute the Ansible playbook"""
        logger.info("Starting playbook execution...")

        # Build command
        cmd = self.get_playbook_cmd() + [self.playbook_path, '-i', self.inventory_path]

        if self.dry_run:
            cmd.append('--check')
            cmd.append('--diff')

        # Add verbosity
        if not self.dry_run:
            cmd.append('-v')

        # Execute
        try:
            logger.info(f"Running: {' '.join(cmd)}")

            # On Windows, we need to handle the process differently
            if self.is_windows:
                result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            else:
                result = subprocess.run(cmd, capture_output=True, text=True)

            # Log output
            if result.stdout:
                logger.info("Playbook output:")
                for line in result.stdout.split('\n'):
                    if line.strip():
                        logger.info(f"  {line}")

            if result.stderr:
                logger.warning("Playbook stderr:")
                for line in result.stderr.split('\n'):
                    if line.strip():
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

        # Print summary
        elapsed = datetime.now() - self.start_time
        print(f"\n{'=' * 60}")
        print(f"  AUTOMATION COMPLETED")
        print(f"  Status: {'✅ SUCCESS' if success else '❌ FAILED'}")
        print(f"  Duration: {elapsed.total_seconds():.2f} seconds")
        print(f"{'=' * 60}\n")

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