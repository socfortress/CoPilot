"""Tests for configurable Velociraptor quarantine artifact resolution (issue #913).

Velociraptor 0.76.x+ added a "forbidden connection test" to the built-in
Linux.Remediation.Quarantine artifact that can roll back a working quarantine.
Operators ship a Custom.Linux.Remediation.Quarantine instead, but CoPilot was
hard-coded to the built-in name. resolve_quarantine_artifact lets a deployment
redirect the built-in names to custom artifacts via env vars, transparently to
the frontend (which keeps sending the built-in name).

Pure-function unit tests — no DB or Velociraptor server.

Run with: cd backend && python -m pytest tests/test_quarantine_artifact_resolution.py
"""

import os
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.connectors.velociraptor.schema.artifacts import (  # noqa: E402
    QuarantineArtifactsEnum,
)
from app.connectors.velociraptor.services.artifacts import (  # noqa: E402
    DEFAULT_LINUX_QUARANTINE_ARTIFACT,
)
from app.connectors.velociraptor.services.artifacts import (
    DEFAULT_WINDOWS_QUARANTINE_ARTIFACT,
)
from app.connectors.velociraptor.services.artifacts import resolve_quarantine_artifact

CUSTOM_LINUX = "Custom.Linux.Remediation.Quarantine"


def test_defaults_when_no_env_override():
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("VELOCIRAPTOR_LINUX_QUARANTINE_ARTIFACT", None)
        os.environ.pop("VELOCIRAPTOR_WINDOWS_QUARANTINE_ARTIFACT", None)
        assert resolve_quarantine_artifact(DEFAULT_LINUX_QUARANTINE_ARTIFACT) == DEFAULT_LINUX_QUARANTINE_ARTIFACT
        assert resolve_quarantine_artifact(DEFAULT_WINDOWS_QUARANTINE_ARTIFACT) == DEFAULT_WINDOWS_QUARANTINE_ARTIFACT


def test_linux_env_override_is_applied():
    with patch.dict(os.environ, {"VELOCIRAPTOR_LINUX_QUARANTINE_ARTIFACT": CUSTOM_LINUX}):
        assert resolve_quarantine_artifact(DEFAULT_LINUX_QUARANTINE_ARTIFACT) == CUSTOM_LINUX
        # Windows is untouched by the Linux override.
        assert resolve_quarantine_artifact(DEFAULT_WINDOWS_QUARANTINE_ARTIFACT) == DEFAULT_WINDOWS_QUARANTINE_ARTIFACT


def test_accepts_enum_member():
    with patch.dict(os.environ, {"VELOCIRAPTOR_LINUX_QUARANTINE_ARTIFACT": CUSTOM_LINUX}):
        assert resolve_quarantine_artifact(QuarantineArtifactsEnum.linux_quarantine) == CUSTOM_LINUX


def test_resolution_is_idempotent():
    # The route resolves once and stores the string; quarantine_host resolves
    # again. Resolving an already-custom name must return it unchanged.
    with patch.dict(os.environ, {"VELOCIRAPTOR_LINUX_QUARANTINE_ARTIFACT": CUSTOM_LINUX}):
        once = resolve_quarantine_artifact(DEFAULT_LINUX_QUARANTINE_ARTIFACT)
        twice = resolve_quarantine_artifact(once)
        assert once == twice == CUSTOM_LINUX


def test_blank_env_var_falls_back_to_default():
    with patch.dict(os.environ, {"VELOCIRAPTOR_LINUX_QUARANTINE_ARTIFACT": "   "}):
        assert resolve_quarantine_artifact(DEFAULT_LINUX_QUARANTINE_ARTIFACT) == DEFAULT_LINUX_QUARANTINE_ARTIFACT


def test_unknown_artifact_returned_unchanged():
    other = "Generic.Client.Info"
    assert resolve_quarantine_artifact(other) == other
