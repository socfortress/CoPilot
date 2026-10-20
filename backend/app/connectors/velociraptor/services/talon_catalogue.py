"""The Velociraptor artifacts CoPilot collects for Talon v2 (talon-analyst D74; plan EA-4, EA-4b).

**This must match talon-analyst's chat catalogue** (``talon.endpoint_catalogue.CATALOGUE``, reviewed
in its PRs): every artifact name, the parameters the model may set, and the parameters its catalogue
pins with their values. A change there needs the same change here, or CoPilot refuses the proposal.
Mirrored from talon-analyst ``main`` at ``fb6991e``.

A Talon collection (an approved ``collect_artifact``; EA-4b's service-account start route reuses
``catalogue_violation``) names an artifact here, exactly as written, sets only its settable
parameters, and sends every pinned parameter at its pinned value. CoPilot's analyst allowlist
(``collection_policy.ANALYST_ARTIFACTS``) is a different list, for people: it isn't used here, and
admins and responders, who approve Talon's proposals, aren't held to it. Two further layers apply on
top: no command, script, quarantine or remediation artifact (``is_response_artifact``), and the
artifact and its dependencies must resolve to Velociraptor's built-in definitions in the host's org
(``collection_policy.enforce_built_in_definitions``).
"""
from dataclasses import dataclass
from dataclasses import field
from types import MappingProxyType
from typing import FrozenSet
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import Tuple

from app.connectors.velociraptor.schema.artifacts import CommandArtifactsEnum
from app.connectors.velociraptor.schema.artifacts import QuarantineArtifactsEnum

OFF = "N"  # how talon-analyst sends a Velociraptor bool switch off


@dataclass(frozen=True)
class TalonArtifact:
    """One catalogue entry: what the model may set, and what is always sent."""

    settable: FrozenSet[str] = frozenset()
    pinned: Mapping[str, str] = field(default_factory=dict)


def _entry(settable: Sequence[str] = (), pinned: Optional[Mapping[str, str]] = None) -> TalonArtifact:
    return TalonArtifact(frozenset(settable), MappingProxyType(dict(pinned or {})))


TALON_CATALOGUE: Mapping[str, TalonArtifact] = MappingProxyType(
    {
        # --- Windows ---
        "Windows.System.Pslist": _entry(
            ("ProcessRegex", "PidRegex", "ExePathRegex", "CommandLineRegex", "UsernameRegex", "UntrustedAuthenticode"),
        ),
        "Windows.Network.Netstat": _entry(),
        "Windows.Network.NetstatEnriched": _entry(
            ("IPRegex", "PortRegex", "ProcessNameRegex", "ProcessPathRegex", "CommandLineRegex", "UsernameRegex"),
            {"DumpProcess": OFF, "KillProcess": OFF},
        ),
        "Windows.System.Services": _entry(("NameRegex", "DisplayNameRegex", "PathNameRegex", "Calculate_hashes", "CertificateInfo")),
        "Windows.System.TaskScheduler": _entry(("Username",), {"AlsoUpload": OFF, "UploadCommands": OFF}),
        "Windows.Sys.StartupItems": _entry((), {"AlsoUpload": OFF}),
        "Windows.Persistence.PermanentWMIEvents": _entry(("AllRootNamespaces",)),
        "Windows.System.DNSCache": _entry(),
        "Windows.Sys.Users": _entry(),
        "Windows.Forensics.Prefetch": _entry(("binaryRegex", "hashRegex", "IncludeFilesAccessed")),
        "Windows.EventLogs.EvtxHunter": _entry(("IocRegex", "WhitelistRegex", "PathRegex", "ChannelRegex", "ProviderRegex", "IdRegex")),
        # --- Linux ---
        "Linux.Sys.Pslist": _entry(("processRegex",)),
        "Linux.Network.Netstat": _entry(("StateRegex",)),
        "Linux.Sys.Users": _entry(),
        "Linux.Sys.LastUserLogin": _entry(("recent_x_days", "MaxCount", "excluded_users")),
        "Linux.Ssh.AuthorizedKeys": _entry((), {"AlsoUpload": OFF}),
        "Linux.Syslog.SSHLogin": _entry(),
    },
)

#: Artifacts that take code, a script or a VQL query.
SCRIPT_ARTIFACTS = frozenset(
    {"Windows.Execute.RemotePowerShellScript", "Linux.Execute.RemoteBashScript", "Generic.Client.VQL", "Windows.System.VBScript"},
)


def is_response_artifact(name: str) -> bool:
    """A command, script, quarantine (the configured overrides included) or remediation artifact:
    never a Talon collection, whatever the catalogue says. A command is ``endpoint_command`` (its
    own card and its hashed audit) and quarantine is ``quarantine_host``."""
    from app.connectors.velociraptor.services.artifacts import (
        resolve_quarantine_artifact,
    )

    quarantine = {a.value for a in QuarantineArtifactsEnum} | {resolve_quarantine_artifact(a.value) for a in QuarantineArtifactsEnum}
    commands = {a.value for a in CommandArtifactsEnum}
    return name in commands | SCRIPT_ARTIFACTS | quarantine or ".remediation." in name.lower()


def catalogue_violation(name: str, parameters: Sequence[Tuple[str, str]]) -> Optional[str]:
    """Why a Talon collection of ``name`` with ``parameters`` (``(key, value)`` pairs, each key
    once) isn't one CoPilot runs, or None."""
    entry = TALON_CATALOGUE.get(name)
    if entry is None or is_response_artifact(name):
        return "not an artifact in Talon's collection catalogue"
    given = dict(parameters)
    for key in given:
        if key not in entry.settable and key not in entry.pinned:
            return f"parameter {key} can't be set for {name}"
    for key, value in entry.pinned.items():
        if given.get(key) != value:
            return f"parameter {key} must be sent as {value} for {name}"
    return None


__all__ = ["OFF", "SCRIPT_ARTIFACTS", "TALON_CATALOGUE", "TalonArtifact", "catalogue_violation", "is_response_artifact"]
