#!/usr/bin/python3
# Copyright (C) 2024, SOCFortress LLP.
# All rights reserved.

# This program is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public
# License (version 2) as published by the FSF - Free Software
# Foundation.

import datetime
import ipaddress
import json
import os
import subprocess
import sys

LOG_FILE = (
    "C:\\Program Files (x86)\\ossec-agent\\active-response\\active-responses.log"
    if os.name == "nt"
    else "/var/ossec/logs/active-responses.log"
)

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
            "active_response": "windows_firewall",
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


def is_valid_ipv4(ip):
    """Checks if an IP address is valid and not private."""
    try:
        ip_obj = ipaddress.IPv4Address(ip)
        return ip_obj.is_global
    except ipaddress.AddressValueError:
        return False


def block_ip(ip):
    """Blocks an IP address on the Windows Firewall."""
    try:
        subprocess.run(
            [
                r"C:\Windows\System32\netsh",
                "advfirewall",
                "firewall",
                "add",
                "rule",
                f"name=SOCFortress Block Outbound {ip}",
                "dir=out",
                "action=block",
                f"remoteip={ip}",
            ],
            check=True,
        )
        return f"Blocked IP {ip} on Windows Firewall"
    except subprocess.CalledProcessError as e:
        return f"Failed to block IP {ip} on Windows Firewall: {e}"


def remove_ip(ip):
    """Removes a blocked IP address from the Windows Firewall."""
    try:
        subprocess.run(
            [r"C:\Windows\System32\netsh", "advfirewall", "firewall", "delete", "rule", f"name=SOCFortress Block Outbound {ip}"],
            check=True,
        )
        return f"Removed blocked IP {ip} from Windows Firewall"
    except subprocess.CalledProcessError as e:
        return f"Failed to remove blocked IP {ip} from Windows Firewall: {e}"


def extract_alert_info(msg, argv):
    """Extracts the action and IP from the alert message."""
    try:
        alert = msg.alert["parameters"]["alert"]
        action = alert["action"]
        ip = alert["ip"]
    except KeyError as e:
        write_debug_file(argv[0], f"Missing key in alert message: {str(e)}")
        sys.exit(OS_INVALID)
    return action, ip


def main(argv):
    write_debug_file(argv[0], {"status": "Started"})
    msg = setup_and_check_message(argv)
    if msg.command < 0:
        sys.exit(OS_INVALID)
    if msg.command == COMMANDS["add"]:
        action, ip = extract_alert_info(msg, argv)
        if not is_valid_ipv4(ip):
            write_debug_file(argv[0], {"status": "failed", "message": f"Invalid IP address {ip}"})
            sys.exit(OS_INVALID)
        if action == "block":
            write_debug_file(argv[0], block_ip(ip))
        if action == "unblock":
            write_debug_file(argv[0], remove_ip(ip))
    elif msg.command == COMMANDS["delete"]:
        # Optionally, include logic here to remove the firewall rule if necessary
        pass
    else:
        write_debug_file(argv[0], "Invalid command")
    write_debug_file(argv[0], "Ended")
    sys.exit(OS_SUCCESS)


if __name__ == "__main__":
    main(sys.argv)
