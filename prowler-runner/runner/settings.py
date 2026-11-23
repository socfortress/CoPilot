"""Runner settings, read once from the environment at startup."""

from __future__ import annotations

import os
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path

# A shorter token is treated as no token: the runner then refuses every request.
MIN_TOKEN_LENGTH = 32

# Proxy settings a deployment may need to reach the cloud APIs. Nothing else from
# the runner's own environment (its token included) ever reaches a scan.
PROXY_VARIABLES = ("HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "no_proxy")

DEFAULT_SCAN_PATH = "/home/prowler/.venv/bin:/usr/local/bin:/usr/bin:/bin"
# Prowler as the official image installs it.
PROWLER_BIN = "/home/prowler/.venv/bin/prowler"
PROWLER_PYTHON = "/home/prowler/.venv/bin/python"


def _int(name: str, default: int, low: int, high: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as error:
        raise ValueError(f"{name} must be a whole number") from error
    if not low <= value <= high:
        raise ValueError(f"{name} must be between {low} and {high}")
    return value


@dataclass(frozen=True)
class Settings:
    token: str | None
    # How to start Prowler's CLI, and Prowler's own interpreter (for the SDK's connection test).
    prowler_cmd: tuple[str, ...]
    prowler_python_cmd: tuple[str, ...]
    compliance_dir: Path
    work_dir: Path
    max_concurrent: int
    scan_timeout: int
    connection_test_timeout: int
    normalize_timeout: int
    job_ttl: int
    max_jobs: int
    scan_home: str
    scan_path: str
    passthrough_env: dict[str, str] = field(default_factory=dict)

    @property
    def token_configured(self) -> bool:
        return bool(self.token) and len(self.token) >= MIN_TOKEN_LENGTH

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            token=os.environ.get("PROWLER_RUNNER_TOKEN", "").strip() or None,
            # Fixed to the image's own Prowler: no setting chooses what the runner executes.
            prowler_cmd=(PROWLER_BIN,),
            prowler_python_cmd=(PROWLER_PYTHON,),
            compliance_dir=Path(os.environ.get("PROWLER_COMPLIANCE_DIR", "/home/prowler/prowler/compliance")),
            work_dir=Path(os.environ.get("PROWLER_WORK_DIR", "/work")),
            max_concurrent=_int("PROWLER_MAX_CONCURRENT", 2, 1, 16),
            # Scans of large AWS accounts can take hours; 12 h is the longest a role session can last.
            scan_timeout=_int("PROWLER_SCAN_TIMEOUT", 14400, 60, 43200),
            connection_test_timeout=_int("PROWLER_CONNECTION_TEST_TIMEOUT", 120, 10, 600),
            normalize_timeout=_int("PROWLER_NORMALIZE_TIMEOUT", 1800, 30, 7200),
            # A finished scan's results are kept this long, or until the backend deletes them.
            job_ttl=_int("PROWLER_JOB_TTL_SECONDS", 86400, 300, 604800),
            max_jobs=_int("PROWLER_MAX_JOBS", 200, 1, 5000),
            scan_home=os.environ.get("PROWLER_SCAN_HOME", "/home/prowler"),
            scan_path=os.environ.get("PROWLER_SCAN_PATH", DEFAULT_SCAN_PATH),
            passthrough_env={name: os.environ[name] for name in PROXY_VARIABLES if os.environ.get(name)},
        )
