#!/usr/bin/env python3
"""
Rollback script in case of configuration errors
"""

import os
import sys
import shutil
from datetime import datetime
from netmiko import ConnectHandler


class ConfigRollback:
    """Rollback configuration to previous state"""

    def __init__(self, device_info):
        self.device = device_info
        self.connection = None

    def connect(self):
        """Connect to device"""
        try:
            self.connection = ConnectHandler(**self.device)
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def backup_config(self):
        """Backup current configuration"""
        output = self.connection.send_command("show running-config")

        backup_file = f"backups/{self.device['name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.cfg"
        os.makedirs('group_vars/all/backups', exist_ok=True)

        with open(backup_file, 'w') as f:
            f.write(output)

        print(f"Backup saved to {backup_file}")
        return backup_file

    def rollback(self, backup_file):
        """Rollback to backup configuration"""
        with open(backup_file, 'r') as f:
            config = f.read()

        self.connection.send_command("configure terminal")
        self.connection.send_config_set(config.split('\n'))
        self.connection.send_command("end")
        self.connection.send_command("write memory")

        print(f"Rollback to {backup_file} completed")

    def disconnect(self):
        """Disconnect from device"""
        if self.connection:
            self.connection.disconnect()


# Usage example
if __name__ == '__main__':
    devices = [
        {
            'device_type': 'cisco_ios',
            'host': '83.1.2.1',
            'username': 'admin',
            'password': 'cisco123',
            'secret': 'cisco123',
            'name': 'ISP'
        }
    ]

    for device in devices:
        rollback = ConfigRollback(device)
        if rollback.connect():
            backup_file = rollback.backup_config()
            # If needed:
            # rollback.rollback(backup_file)
            rollback.disconnect()