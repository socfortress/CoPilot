"""Stands in for runner/helpers/test_connection.py in the runner's tests.

Reads the same stdin and answers the same way, choosing the outcome from the
client secret (Azure, Microsoft 365) or the access key id (AWS). Records its
arguments and input in $FAKE_RECORD_DIR/connection.json (test-only).
"""

import json
import os
import sys
import time
from pathlib import Path

PREFIX = "PROWLER_RUNNER_RESULT "


def answer(ok, error_class=None):
    sys.stdout.write(PREFIX + json.dumps({"ok": ok, "error_class": error_class}) + "\n")


def main():
    payload = json.loads(sys.stdin.read())
    record_dir = os.environ.get("FAKE_RECORD_DIR")
    if record_dir:
        Path(record_dir, "connection.json").write_text(
            json.dumps({"argv": sys.argv, "isolated": sys.flags.isolated, "payload": payload, "env": dict(os.environ)}),
        )
    auth = payload["auth"]
    marker = auth.get("client_secret") or auth.get("aws_access_key_id") or ""
    if "sleep" in marker:
        time.sleep(60)
    if "crash" in marker:
        sys.exit(1)
    if "noisy" in marker:
        print("Error: the secret was " + marker)
        answer(False, "AzureClientAuthenticationError")
        return
    if "wrongtenant" in marker:
        answer(False, "M365InvalidProviderIdError")
        return
    if "bad" in marker:
        answer(False, "AzureClientAuthenticationError")
        return
    answer(True)


if __name__ == "__main__":
    main()
