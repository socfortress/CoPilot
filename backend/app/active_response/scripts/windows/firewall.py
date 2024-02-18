#!/usr/bin/python3
import os
import sys
import json
import datetime
import json
import subprocess  # Import subprocess to execute shell commands
from pathlib import PureWindowsPath, PurePosixPath
import ipaddress

if os.name == 'nt':
    LOG_FILE = "C:\\Program Files (x86)\\ossec-agent\\active-response\\active-responses.log"
else:
    LOG_FILE = "/var/ossec/logs/active-responses.log"

ADD_COMMAND = 0
DELETE_COMMAND = 1
CONTINUE_COMMAND = 2
ABORT_COMMAND = 3

OS_SUCCESS = 0
OS_INVALID = -1

class message:
    def __init__(self):
        self.alert = ""
        self.command = 0


def write_debug_file(ar_name, msg):
    with open(LOG_FILE, mode="a") as log_file:
        ar_name_posix = str(PurePosixPath(PureWindowsPath(ar_name[ar_name.find("active-response"):])))
        log_msg = {
            "timestamp": datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S'),
            "ar_name": "windows_firewall",
            "message": json.loads(msg) if isinstance(msg, str) and msg.strip().startswith('{') else msg
        }
        log_file.write(json.dumps(log_msg) + "\n")

def setup_and_check_message(argv):
    input_str = ""
    for line in sys.stdin:
        input_str = line
        break
    write_debug_file(argv[0], input_str)
    try:
        data = json.loads(input_str)
    except ValueError:
        write_debug_file(argv[0], 'Decoding JSON has failed, invalid input format')
        message.command = OS_INVALID
        return message
    message.alert = data
    command = data.get("command")
    if command == "add":
        message.command = ADD_COMMAND
    elif command == "delete":
        message.command = DELETE_COMMAND
    else:
        message.command = OS_INVALID
        write_debug_file(argv[0], 'Not valid command: ' + command)
    return message

def is_valid_ipv4(ip):
    try:
        ip_obj = ipaddress.IPv4Address(ip)
        return ip_obj.is_global
    except ipaddress.AddressValueError:
        return False

def main(argv):
    write_debug_file(argv[0], {"status": "Started"})
    msg = setup_and_check_message(argv)
    if msg.command < 0:
        sys.exit(OS_INVALID)
    if msg.command == ADD_COMMAND:
        """ Extract the keys and values from the alert """

        alert = msg.alert["parameters"]["alert"]
        ip = alert["ip"]

        # Validate the IP address
        if not is_valid_ipv4(ip):
            write_debug_file(argv[0], {"status": "failed", "message": f"Invalid IP address {ip}"})
            sys.exit(OS_INVALID)


        """ Start Custom Action Add """
        # Block IP address on Windows Firewall for outbound connections
        try:
            subprocess.run(["netsh", "advfirewall", "firewall", "add", "rule",
                            f"name=Block Outbound {ip}", "dir=out", "action=block",
                            f"remoteip={ip}"], check=True)
            write_debug_file(argv[0], f"Blocked IP {ip} on Windows Firewall")
        except subprocess.CalledProcessError as e:
            write_debug_file(argv[0], f"Failed to block IP {ip} on Windows Firewall: {e}")
        """ End Custom Action Add """

    elif msg.command == DELETE_COMMAND:
        """ Start Custom Action Delete """
        # Optionally, include logic here to remove the firewall rule if necessary
        """ End Custom Action Delete """

    else:
        write_debug_file(argv[0], "Invalid command")

    write_debug_file(argv[0], "Ended")
    sys.exit(OS_SUCCESS)

if __name__ == "__main__":
    main(sys.argv)
