#!/usr/bin/env python3
"""
Configuration validation script with HTML reporting
"""

import os
import json
import sys

import yaml
import socket
from datetime import datetime
from pathlib import Path
from netmiko import ConnectHandler
import logging

# Setup logging
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f"validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ConfigValidator:
    """Validate network device configurations"""

    def __init__(self):
        self.devices = []
        self.results = {}

    def load_inventory(self, inventory_file="inventory.yml"):
        """Load device inventory"""
        try:
            with open(inventory_file, 'r') as f:
                inventory = yaml.safe_load(f)

            # Extract devices from inventory
            for group in inventory.get('all', {}).get('children', {}):
                for host, host_vars in inventory.get('all', {}).get('children', {}).get(group, {}).get('hosts',
                                                                                                       {}).items():
                    self.devices.append({
                        'name': host,
                        'host': host_vars.get('ansible_host'),
                        'username': host_vars.get('ansible_user', 'admin'),
                        'password': host_vars.get('ansible_password', 'cisco123'),
                        'device_type': host_vars.get('device_type', 'cisco_ios'),
                        'secret': host_vars.get('ansible_become_password', 'cisco123'),
                        'group': group
                    })

            logger.info(f"Loaded {len(self.devices)} devices from inventory")
            return True
        except Exception as e:
            logger.error(f"Error loading inventory: {str(e)}")
            return False

    def connect_to_device(self, device):
        """Connect to a device"""
        try:
            connection = ConnectHandler(**device)
            connection.enable()
            return connection
        except Exception as e:
            logger.error(f"Error connecting to {device['name']}: {str(e)}")
            return None

    def validate_interface(self, conn, interface, expected_ip, expected_status='up'):
        """Validate interface configuration"""
        output = conn.send_command(f"show interfaces {interface}")

        if f"Line protocol is {expected_status}" in output.lower():
            if expected_ip:
                if expected_ip in output:
                    return True, f"Interface {interface} is up with IP {expected_ip}"
                else:
                    return False, f"Interface {interface} expected IP {expected_ip} not found"
            return True, f"Interface {interface} is {expected_status}"
        else:
            return False, f"Interface {interface} is not {expected_status}"

    def validate_route(self, conn, network, mask, next_hop):
        """Validate static route"""
        output = conn.send_command(f"show ip route {network}")

        if f"{network} {mask}" in output and next_hop in output:
            return True, f"Route {network}/{mask} via {next_hop} exists"
        else:
            return False, f"Route {network}/{mask} not found"

    def validate_bgp(self, conn, as_number, neighbors=None):
        """Validate BGP configuration"""
        output = conn.send_command("show ip bgp summary")

        if f"AS{as_number}" in output:
            if neighbors:
                for neighbor in neighbors:
                    if neighbor not in output:
                        return False, f"BGP neighbor {neighbor} not found"
            return True, f"BGP AS {as_number} configured correctly"
        else:
            return False, f"BGP AS {as_number} not found"

    def validate_device(self, device):
        """Validate a single device"""
        logger.info(f"Validating {device['name']}...")

        conn = self.connect_to_device(device)
        if not conn:
            return {
                'device': device['name'],
                'status': 'FAILED',
                'errors': ['Connection failed'],
                'checks': []
            }

        checks = []
        status = 'PASSED'
        errors = []

        # Perform device-specific validation
        if device['group'] == 'isp':
            # Check interfaces
            checks.append(self.validate_interface(conn, 's0/0/0', '83.1.2.1'))
            checks.append(self.validate_interface(conn, 'g0/0', '83.1.1.1'))
            checks.append(self.validate_interface(conn, 'g0/1', '193.10.160.223'))

            # Check routes
            checks.append(self.validate_route(conn, '0.0.0.0', '0.0.0.0', '193.10.160.1'))
            checks.append(self.validate_route(conn, '192.168.100.0', '255.255.255.0', '83.1.1.2'))
            checks.append(self.validate_route(conn, '192.168.200.0', '255.255.255.0', '83.1.2.2'))

            # Check BGP
            checks.append(self.validate_bgp(conn, '65000', ['193.10.161.250']))

        elif device['group'] == 'jkpg':
            checks.append(self.validate_interface(conn, 'g0/0', '83.1.1.2'))
            checks.append(self.validate_interface(conn, 'g0/1', '192.168.100.11'))
            checks.append(self.validate_route(conn, '0.0.0.0', '0.0.0.0', '83.1.1.1'))

            # Check GRE tunnel
            output = conn.send_command("show interface tunnel 0")
            if "Tunnel0" in output and "10.1.1.1" in output:
                checks.append((True, "GRE Tunnel configured"))
            else:
                checks.append((False, "GRE Tunnel not configured"))

        elif device['group'] == 'gbg':
            checks.append(self.validate_interface(conn, 's0/0/0', '83.1.2.2'))
            checks.append(self.validate_interface(conn, 'lo0', '192.168.200.1'))
            checks.append(self.validate_route(conn, '0.0.0.0', '0.0.0.0', '83.1.2.1'))
            checks.append(self.validate_bgp(conn, '65001', ['83.1.2.1']))

        # Update status
        for success, message in checks:
            if not success:
                status = 'FAILED'
                errors.append(message)

        conn.disconnect()

        return {
            'device': device['name'],
            'status': status,
            'errors': errors,
            'checks': checks,
            'timestamp': datetime.now().isoformat()
        }

    def validate_all(self):
        """Validate all devices"""
        for device in self.devices:
            result = self.validate_device(device)
            self.results[device['name']] = result

        return self.results

    def generate_report(self):
        """Generate validation report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total': len(self.results),
                'passed': sum(1 for r in self.results.values() if r['status'] == 'PASSED'),
                'failed': sum(1 for r in self.results.values() if r['status'] == 'FAILED')
            },
            'devices': self.results
        }

        # Save JSON report
        report_file = LOG_DIR / f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"Report saved to {report_file}")

        # Print summary
        print(f"\n{'=' * 60}")
        print(f"VALIDATION SUMMARY")
        print(f"{'=' * 60}")
        print(f"Total Devices: {report['summary']['total']}")
        print(f"✅ Passed: {report['summary']['passed']}")
        print(f"❌ Failed: {report['summary']['failed']}")
        print(f"{'=' * 60}\n")

        # Print details
        for device_name, result in report['devices'].items():
            status_color = Colors.GREEN if result['status'] == 'PASSED' else Colors.RED
            print(f"{status_color}{device_name}: {result['status']}{Colors.RESET}")
            if result['errors']:
                for error in result['errors']:
                    print(f"  ❌ {error}")
            print()

        return report


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    RESET = '\033[0m'


def main():
    validator = ConfigValidator()

    if not validator.load_inventory():
        sys.exit(1)

    validator.validate_all()
    report = validator.generate_report()

    # Exit with code if validation failed
    if report['summary']['failed'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()