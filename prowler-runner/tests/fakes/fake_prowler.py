"""Stands in for the ``prowler`` CLI in the runner's tests.

The runner starts it as ``python fake_prowler.py <provider> <options...>`` with the
scan's environment, in the job's directory. It records what it was given in
``invocation.json`` there (test-only: secrets included), then behaves according to
a ``fake_mode_*`` name among the ``--excluded-checks`` values:

- (none): write the sample OCSF file, an HTML and a CSV report, compliance CSVs, log
  one ERROR line, exit 0
- fake_mode_exit3: the same, exit 3
- fake_mode_auth: log a CRITICAL assume-role error, exit 1
- fake_mode_expired_secret: log Azure's refusal of an expired client secret as Prowler
  prints it (not JSON-escaped: the message spans lines), exit 1
- fake_mode_argparse: print a usage error, exit 2
- fake_mode_sleep: start a child that sleeps, write its pid to child.pid, sleep
- fake_mode_bad_output: write an OCSF file that isn't JSON, exit 0
- fake_mode_no_output: write nothing, exit 0
- fake_mode_long_line: print a 200 KB line first, then as with no mode
"""

import json
import os
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "aws_sample.ocsf.json"


def option(argv, name):
    for argument in argv:
        if argument.startswith(name + "="):
            return argument.split("=", 1)[1]
    return None


def values_after(argv, name):
    if name not in argv:
        return []
    values = []
    for argument in argv[argv.index(name) + 1 :]:
        if argument.startswith("-"):
            break
        values.append(argument)
    return values


def record(argv):
    data = {"argv": argv, "env": dict(os.environ), "cwd": os.getcwd()}
    credentials = option(argv, "--credentials-file")
    if credentials:
        path = Path(credentials)
        data["credentials_file"] = {
            "exists": path.exists(),
            "mode": stat.S_IMODE(path.stat().st_mode) if path.exists() else None,
            "content": json.loads(path.read_text()) if path.exists() else None,
        }
    Path("invocation.json").write_text(json.dumps(data))


def log(level, message):
    print(
        json.dumps({"timestamp": "2026-11-23 12:00:00,000", "filename": "fake.py:1", "level": level, "module": "fake", "message": message}),
        flush=True,
    )


def write_outputs(out_dir, name):
    out_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(FIXTURE, out_dir / f"{name}.ocsf.json")
    (out_dir / f"{name}.html").write_text("<html><body>report</body></html>")
    (out_dir / f"{name}.csv").write_text("PROVIDER;CHECK_ID;STATUS\naws;iam_root_mfa_enabled;FAIL\n")
    compliance = out_dir / "compliance"
    compliance.mkdir(exist_ok=True)
    (compliance / f"{name}_cis_5.0_aws.csv").write_text("x\n")


def main():
    argv = sys.argv[1:]
    record(argv)
    modes = [value for value in values_after(argv, "--excluded-checks") if value.startswith("fake_mode_")]
    mode = modes[0] if modes else None
    out_dir = Path(option(argv, "--output-directory"))
    name = option(argv, "--output-filename")

    if mode == "fake_mode_expired_secret":
        print(
            '{"timestamp": "2026-11-24 09:00:01,100", "filename": "azure_provider.py:940", "level": "ERROR", '
            '"module": "azure_provider", "message": "ClientAuthenticationError[933] -- DefaultAzureCredential failed '
            "to retrieve a token from the included credentials.\nAttempted credentials:\n\tEnvironmentCredential: "
            "Authentication failed: AADSTS7000222: The provided client secret keys for app 'SensitiveAppId' are "
            'expired.\nTo mitigate this issue, please refer to the troubleshooting guidelines."}',
            flush=True,
        )
        log("CRITICAL", "AzureHTTPResponseError[404]: AzureHTTPResponseError[2010]: Error in HTTP response from Azure")
        sys.exit(1)
    if mode == "fake_mode_auth":
        log("CRITICAL", "AWSAssumeRoleError[1012]: AWS assume role error - arn:aws:iam::123456789012:role/SensitiveRoleName was refused")
        sys.exit(1)
    if mode == "fake_mode_argparse":
        print("usage: prowler [-h] ...\nprowler: error: unrecognized arguments", file=sys.stderr)
        sys.exit(2)
    if mode == "fake_mode_sleep":
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
        Path("child.pid").write_text(str(child.pid))
        time.sleep(120)
        sys.exit(0)
    if mode == "fake_mode_bad_output":
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{name}.ocsf.json").write_text('[{"metadata": {"event_code": "x"}, ')
        sys.exit(0)
    if mode == "fake_mode_no_output":
        sys.exit(0)
    if mode == "fake_mode_long_line":
        print("x" * 200_000, flush=True)

    print("plain text that isn't a log record", flush=True)
    log("ERROR", "ClientError[88]: An error occurred (AccessDenied) when calling the GetBucketPolicy operation")
    write_outputs(out_dir, name)
    sys.exit(3 if mode == "fake_mode_exit3" else 0)


if __name__ == "__main__":
    main()
