#!/usr/bin/python3
# Copyright (C) 2025, SOCFortress LLC.
# All rights reserved.

# This program is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public
# License (version 2) as published by the FSF - Free Software
# Foundation.

import datetime
import json
import os
import re
import subprocess
import sys

LOG_FILE = "/var/ossec/logs/active-responses.log"
HOSTS_FILE = "/etc/hosts"
SINKHOLE_IP = "127.0.0.1"  # Loopback address for sinkholing

COMMANDS = {"add": 0, "delete": 1, "continue": 2, "abort": 3}

OS_SUCCESS = 0
OS_INVALID = -1


class Message:
    def __init__(self, alert="", command=0):
        self.alert = alert
        self.command = command


def write_debug_file(ar_name, msg):
    """Writes a debug message to the log file."""
    with open(LOG_FILE, mode="a") as log_file:
        log_msg = {
            "timestamp": datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
            "active_response": "domain_sinkhole",
            "message": json.loads(msg) if isinstance(msg, str) and msg.strip().startswith("{") else msg,
        }
        log_file.write(json.dumps(log_msg) + "\n")


def setup_and_check_message(argv):
    """Reads and validates the input message."""
    input_str = next(sys.stdin, "")
    write_debug_file(argv[0], input_str)
    try:
        data = json.loads(input_str)
    except ValueError:
        write_debug_file(argv[0], "Decoding JSON has failed, invalid input format")
        return Message(command=OS_INVALID)
    command = COMMANDS.get(data.get("command"), OS_INVALID)
    if command == OS_INVALID:
        write_debug_file(argv[0], "Not valid command: " + data.get("command"))
    return Message(alert=data, command=command)


def is_valid_domain(domain):
    """Checks if a domain name is valid."""
    # Basic domain validation regex
    pattern = r"^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)+([A-Za-z]|[A-Za-z][A-Za-z0-9\-]*[A-Za-z0-9])$"
    return bool(re.match(pattern, domain))


def sinkhole_domain(domain):
    """Adds a domain to /etc/hosts pointing to loopback."""
    try:
        # Check if domain already exists in hosts file
        with open(HOSTS_FILE, "r") as f:
            hosts_content = f.read()

        if f"{SINKHOLE_IP} {domain}" in hosts_content:
            return f"Domain {domain} is already sinkholed"

        # Add the domain to hosts file
        with open(HOSTS_FILE, "a") as f:
            f.write(f"\n{SINKHOLE_IP} {domain} # Added by SOCFortress sinkhole\n")

        # Flush DNS cache if dnsmasq is running
        try:
            subprocess.run(["systemctl", "restart", "dnsmasq"], check=False)
        except (subprocess.SubprocessError, FileNotFoundError):
            # More specific exceptions for when systemctl doesn't exist or fails
            pass  # It's okay if dnsmasq isn't installed

        return f"Sinkholed domain {domain} to {SINKHOLE_IP}"
    except Exception as e:
        return f"Failed to sinkhole domain {domain}: {str(e)}"


def remove_sinkholed_domain(domain):
    """Removes a domain from the /etc/hosts file."""
    try:
        # Read hosts file
        with open(HOSTS_FILE, "r") as f:
            hosts_lines = f.readlines()

        # Filter out the domain entry
        new_hosts = [line for line in hosts_lines if not (domain in line and "Added by SOCFortress sinkhole" in line)]

        # Write back the file without the domain
        with open(HOSTS_FILE, "w") as f:
            f.writelines(new_hosts)

        # Flush DNS cache if dnsmasq is running
        try:
            subprocess.run(["systemctl", "restart", "dnsmasq"], check=False)
        except (subprocess.SubprocessError, FileNotFoundError):
            # More specific exceptions for when systemctl doesn't exist or fails
            pass  # It's okay if dnsmasq isn't installed

        return f"Removed sinkholed domain {domain}"
    except Exception as e:
        return f"Failed to remove sinkholed domain {domain}: {str(e)}"


def extract_alert_info(msg, argv):
    """Extracts the action and domain from the alert message."""
    try:
        alert = msg.alert["parameters"]["alert"]
        action = alert.get("action", "sinkhole")  # Default to block if not specified
        domain = alert.get("value")

        if not domain:
            write_debug_file(argv[0], "No domain specified in alert")
            sys.exit(OS_INVALID)
    except KeyError as e:
        write_debug_file(argv[0], f"Missing key in alert message: {str(e)}")
        sys.exit(OS_INVALID)
    return action, domain


def main(argv):
    write_debug_file(argv[0], {"status": "Started"})

    # Check if running as root (required to modify /etc/hosts)
    if os.geteuid() != 0:
        write_debug_file(argv[0], {"status": "failed", "message": "This script must run as root to modify /etc/hosts"})
        sys.exit(OS_INVALID)

    msg = setup_and_check_message(argv)
    if msg.command < 0:
        sys.exit(OS_INVALID)

    if msg.command == COMMANDS["add"]:
        action, domain = extract_alert_info(msg, argv)

        if not is_valid_domain(domain):
            write_debug_file(argv[0], {"status": "failed", "message": f"Invalid domain name: {domain}"})
            sys.exit(OS_INVALID)

        if action == "sinkhole":  # Handle both "block" and "sinkhole" actions
            result = sinkhole_domain(domain)
            write_debug_file(argv[0], result)
        elif action == "remove_sinkhole":
            result = remove_sinkholed_domain(domain)
            write_debug_file(argv[0], result)
        else:
            write_debug_file(argv[0], f"Unknown action: {action}")

    elif msg.command == COMMANDS["delete"]:
        # The delete command could be used to clean up any persistent changes
        # For this implementation, we don't need any cleanup
        pass

    else:
        write_debug_file(argv[0], "Invalid command")

    write_debug_file(argv[0], "Ended")
    sys.exit(OS_SUCCESS)


if __name__ == "__main__":
    main(sys.argv)
