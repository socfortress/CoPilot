"""Which artifacts an analyst may launch through ``POST /api/artifacts/collect``.

``/collect`` admits admin and analyst. Running commands and remediation on an endpoint is admin
and responder only (``/command``, ``/quarantine``, CoPilot Actions). ``/collect`` used to accept
any artifact in the host's OS list, which includes ``Windows.System.PowerShell`` and the
``*.Remediation.*`` artifacts, so an analyst could run an arbitrary command -- or quarantine a
host -- by collecting one with a ``Command`` parameter.

For anyone but an admin or responder the rule is an allowlist, and it fails closed. The
artifact is read from Velociraptor *in the host's org*, together with every artifact it depends
on (``artifact_definitions(names=[X], deps=true)``, which resolves dependencies with
Velociraptor's own VQL parser, as the launcher does when it compiles the collection):

1. The artifact and every dependency must be in ``ANALYST_ARTIFACTS``.
2. Each of them must resolve to Velociraptor's shipped, compiled-in definition
   (``compiled_in``). Velociraptor sets that flag only for artifacts built into the binary and
   clears it on anything loaded from YAML, so a child org that shadows a built-in name with its
   own definition -- the org's override check only looks at the org's own repository -- or a
   custom artifact claiming the flag, is refused. This is the primary gate: the allowlist was
   reviewed against the shipped definitions, and only those may run.
3. Every parameter the caller sets must be on the artifact's known-safe list, or equal the
   artifact's own default (the frontend sends every default back; leaving one unchanged is not
   choosing it).
4. Defence in depth: each definition must still look read-only -- no required or implied
   permission beyond FILESYSTEM_READ and MACHINE_STATE (which every client collection implies,
   services/launcher/verifier.go), no ``imports`` or ``tools``, no call to a function with
   side effects (``_FORBIDDEN_CALL``) and no ``Artifact.X`` reference outside the list. The VQL
   is scanned both as written and with comments removed, with backticks dropped, so
   a backtick-quoted execve, ``execve/**/(`` and a backtick-quoted, hyphenated Artifact name are seen.

``ANALYST_ARTIFACTS`` was generated from Velociraptor's built-in definitions (master, October
2026) and every function those artifacts call was reviewed by hand: they parse, list, hash and
read (pslist, handles, netstat, glob, read_file, the parse_* family, sqlite, yara over files,
wmi SELECTs with fixed queries, token information). ``Windows.Detection.Yara.PhysicalMemory``
(``winpmem()`` stops and deletes a named service, then loads a kernel driver) and
``Windows.ETW.DotNetRundown`` (``watch_etw()`` starts an ETW session) were removed in that
review, and ``Linux.Forensics.Journal.Fields`` because rule 4 reads "panic (" in a comment
inside one of its parse_binary profile strings; it is harmless, but the scan is not weakened
for it. A parameter is listed as safe when it only narrows what is read (regex, glob, time,
number, bool or choice) and its name does not look like a tool path, URL, command, script,
accessor, output or an execute/delete/kill/upload/dump toggle. To let analysts collect another
artifact, review what it calls and add it here with the parameters they may set; rules 2 and 4
still apply to it at run time. Admins and responders are not restricted by this module.
"""
import re
from typing import Dict
from typing import FrozenSet
from typing import List
from typing import Optional

from fastapi import HTTPException
from loguru import logger

from app.auth.models.users import RoleEnum
from app.connectors.velociraptor.schema.artifacts import CommandArtifactsEnum
from app.connectors.velociraptor.schema.artifacts import QuarantineArtifactsEnum
from app.connectors.velociraptor.utils.validation import vql_string_literal_value

# Roles that may run response artifacts (the roles /command and /quarantine admit).
RESPONSE_ROLES = frozenset({RoleEnum.admin, RoleEnum.responder})

# Permissions every client collection implies (services/launcher/verifier.go).
READ_ONLY_PERMISSIONS = frozenset({"FILESYSTEM_READ", "MACHINE_STATE"})

# VQL functions and plugins with side effects. Every function Velociraptor registers with an
# EXECVE, FILESYSTEM_WRITE, NETWORK, IMPERSONATION or server permission, plus those that change
# the endpoint while declaring only MACHINE_STATE (winpmem, proc_dump, watch_etw, ...).
FORBIDDEN_CALLS = frozenset(
    {
        "adx_upload",
        "amsi",
        "artifact_delete",
        "artifact_set",
        "artifact_set_metadata",
        "azure_monitor_upload",
        "backup",
        "backup_restore",
        "cancel_flow",
        "carve_evtx",
        "client_create",
        "client_delete",
        "client_set_metadata",
        "collect",
        "collect_client",
        "compress",
        "copy",
        "create_flow_download",
        "create_hunt_download",
        "create_notebook_download",
        "delete_events",
        "delete_flow",
        "elastic_upload",
        "eval",
        "execve",
        "file_store_delete",
        "gcs_pubsub_publish",
        "http_client",
        "hunt",
        "hunt_add",
        "hunt_delete",
        "hunt_update",
        "impersonate",
        "import_collection",
        "inventory_add",
        "kill",
        "label",
        "logscale_upload",
        "mail",
        "mkdir",
        "netcat",
        "notebook_create",
        "notebook_delete",
        "notebook_update",
        "notebook_update_cell",
        "org_create",
        "org_delete",
        "panic",
        "pk_encrypt",
        "proc_dump",
        "pskill",
        "query",
        "rekey",
        "repack",
        "rm",
        "rmdir",
        "rsyslog",
        "s3",
        "sandbox",
        "secret_add",
        "secret_modify",
        "send_event",
        "server_set_metadata",
        "shell",
        "shell_session",
        "shell_session_control",
        "sigma",
        "smb",
        "splunk_upload",
        "sql",
        "ssh",
        "tempdir",
        "tempfile",
        "unzip",
        "user_create",
        "user_delete",
        "user_grant",
        "watch_etw",
        "winpmem",
        "yarax",
    },
)
# Families matched by prefix or suffix: upload*, write_*, reg_set_* / reg_rm_*, service_*, *_upload,
# add_/rm_/set_*_monitoring.
_FORBIDDEN_CALL = re.compile(
    r"(?i)(?<![\w.])("
    + "|".join(sorted(FORBIDDEN_CALLS, key=len, reverse=True))
    + r"|upload\w*|write_\w+|reg_(?:set|rm)\w*|service_\w+|\w+_upload|(?:add|rm|set)_\w*monitoring)\s*\(",
)
_ARTIFACT_REFERENCE = re.compile(r"(?i)(?<![\w.])Artifact\.([\w.\-]+)")

# Artifacts analysts may collect, each with the parameters they may set.
ANALYST_ARTIFACTS: Dict[str, FrozenSet[str]] = {
    "Linux.Applications.Chrome.Extensions": frozenset(),
    "Linux.Debian.AptSources": frozenset(),
    "Linux.Detection.AnomalousFiles": frozenset({"MaxNormalSize"}),
    "Linux.Forensics.ImmutableFiles": frozenset({"DoNotFollowSymlinks", "OneFilesystem", "SearchFilesGlob"}),
    "Linux.Mounts": frozenset(),
    "Linux.Network.Netstat": frozenset({"StateRegex"}),
    "Linux.Network.NetstatEnriched": frozenset(
        {"CallChainRegex", "ConnectionStatusRegex", "IPRegex", "PortRegex", "ProcessNameRegex", "UsernameRegex"},
    ),
    "Linux.Proc.Arp": frozenset(),
    "Linux.Proc.Modules": frozenset(),
    "Linux.Ssh.KnownHosts": frozenset(),
    "Linux.Ssh.PrivateKeys": frozenset({"LocalFilesystemOnly"}),
    "Linux.Sys.ACPITables": frozenset(),
    "Linux.Sys.BashHistory": frozenset({"SearchRegex", "TargetGlob", "WhitelistRegex"}),
    "Linux.Sys.CPUTime": frozenset(),
    "Linux.Sys.Groups": frozenset(),
    "Linux.Sys.LastUserLogin": frozenset({"LoginType", "MaxCount", "excluded_users", "recent_x_days"}),
    "Linux.Sys.LogGrep": frozenset({"GrepRegex", "TargetGlob", "WhitelistRegex"}),
    "Linux.Sys.LogHunter": frozenset({"ExcludeDirectoryRegex", "FilterRegex", "SearchRegex"}),
    "Linux.Sys.Maps": frozenset({"processRegex"}),
    "Linux.Sys.Pslist": frozenset({"processRegex"}),
    "Linux.Sys.SUID": frozenset(),
    "Linux.Sys.Users": frozenset(),
    "Linux.Syslog.SSHLogin": frozenset(),
    "Linux.Users.InteractiveUsers": frozenset(),
    "MacOS.Applications.Chrome.History": frozenset({"userRegex"}),
    "MacOS.Applications.MRU": frozenset(),
    "MacOS.Detection.InstallHistory": frozenset(),
    "MacOS.Forensics.AppleDoubleZip": frozenset({"ZipGlob"}),
    "MacOS.Forensics.FSEvents": frozenset({"DateAfter", "DateBefore", "FlagsRegex", "Glob", "MaxFileSize"}),
    "MacOS.Network.Netstat": frozenset(
        {
            "AlsoCollectFullProcessTree",
            "CallChainRegex",
            "ConnectionStatusRegex",
            "IPRegex",
            "PortRegex",
            "ProcessNameRegex",
            "UsernameRegex",
        },
    ),
    "MacOS.System.Dock": frozenset({"DockGlob"}),
    "MacOS.System.QuarantineEvents": frozenset({"QuarantineGlob"}),
    "MacOS.System.TCC": frozenset({"TCCGlob"}),
    "MacOS.System.TimeMachine": frozenset({"TimeMachineGlob"}),
    "MacOS.System.Users": frozenset({"OnlyShowRealUsers", "UserPlistGlob"}),
    "MacOS.System.Wifi": frozenset({"WifiGlob"}),
    "Windows.Analysis.EvidenceOfDownload": frozenset({"ZoneIdRegex"}),
    "Windows.Applications.ChocolateyPackages": frozenset(),
    "Windows.Applications.IISLogs": frozenset({"MoreRecentThan", "SearchRegex", "WhitelistRegex"}),
    "Windows.Applications.OfficeMacros": frozenset({"officeFileSearchGlob"}),
    "Windows.Applications.TeamViewer.Incoming": frozenset(
        {"DateAfter", "DateBefore", "FileGlob", "SourceHostRegex", "TeamViewerIDRegex", "UserRegex", "VSSAnalysisAge"},
    ),
    "Windows.Attack.ParentProcess": frozenset(),
    "Windows.Attack.Prefetch": frozenset(),
    "Windows.Attack.UnexpectedImagePath": frozenset(),
    "Windows.Carving.USN": frozenset({"DateAfter", "DateBefore", "FileNameRegex"}),
    "Windows.Detection.Amcache": frozenset({"AMCacheGlob", "NameRegex", "SHA1Regex", "VersionRegex"}),
    "Windows.Detection.BinaryRename": frozenset({"TargetGlob"}),
    "Windows.Detection.EnvironmentVariables": frozenset(
        {"EnvironmentVariableRegex", "FilterValueRegex", "PidRegex", "ProcessNameRegex", "WhitelistValueRegex"},
    ),
    "Windows.Detection.ForwardedImports": frozenset({"DLLGlob", "ExcludeRegex", "LogPeriod"}),
    "Windows.Detection.Impersonation": frozenset(),
    "Windows.Detection.Mutants": frozenset({"MutantNameRegex", "MutantWhitelistRegex", "processRegex"}),
    "Windows.EventLogs.AlternateLogon": frozenset(),
    "Windows.EventLogs.DHCP": frozenset({"eventDirGlob"}),
    "Windows.EventLogs.Evtx": frozenset({"ChannelRegex", "EndDate", "EvtxGlob", "IDRegex", "StartDate", "VSSAnalysisAge"}),
    "Windows.EventLogs.ExplicitLogon": frozenset(
        {
            "DateAfter",
            "DateBefore",
            "EvtxGlob",
            "ProcessNameRegex",
            "ProcessNameWhitelist",
            "ServerRegex",
            "ServerWhitelist",
            "UsernameRegex",
            "UsernameWhitelist",
            "VSSAnalysisAge",
        },
    ),
    "Windows.EventLogs.Kerberoasting": frozenset({"EvtxGlob", "VSSAnalysisAge"}),
    "Windows.EventLogs.Modifications": frozenset({"DateAfter", "DateBefore", "ProviderRegex"}),
    "Windows.EventLogs.PowershellModule": frozenset({"ContextRegex", "DateAfter", "DateBefore", "PayloadRegex", "VSSAnalysisAge"}),
    "Windows.EventLogs.PowershellScriptblock": frozenset(
        {"DateAfter", "DateBefore", "EvtxGlob", "LogLevel", "SearchStrings", "StringWhitelist", "VSSAnalysisAge"},
    ),
    "Windows.EventLogs.RDPAuth": frozenset(
        {"DateAfter", "DateBefore", "SourceIPRegex", "UserNameRegex", "UserNameWhitelist", "VSSAnalysisAge"},
    ),
    "Windows.EventLogs.ScheduledTasks": frozenset(
        {
            "DateAfter",
            "DateBefore",
            "IocRegex",
            "SecurityEventRegex",
            "TaskActionRegex",
            "TaskActionWhitelist",
            "TaskNameRegex",
            "TaskNameWhitelist",
            "TaskSchedulerEventRegex",
            "UserNameRegex",
            "VSSAnalysisAge",
        },
    ),
    "Windows.EventLogs.ServiceCreationComspec": frozenset({"ComspecRegex", "VSSAnalysisAge"}),
    "Windows.EventLogs.Symantec": frozenset({"DateAfter", "DateBefore", "IgnoreRegex", "TargetRegex"}),
    "Windows.EventLogs.Telerik": frozenset({"DateAfter", "DateBefore", "EvtxGlob", "IocRegex", "VSSAnalysisAge", "WhitelistRegex"}),
    "Windows.Forensics.Amcache": frozenset(
        {
            "File",
            "Generic",
            "InventoryApplication",
            "InventoryApplicationFile",
            "InventoryApplicationShortcut",
            "InventoryDriverPackage",
            "NTFS_CACHE_SIZE",
            "Programs",
            "amCacheGlob",
        },
    ),
    "Windows.Forensics.FilenameSearch": frozenset(),
    "Windows.Forensics.PartitionTable": frozenset({"MagicRegex", "NameRegex", "SectorSize"}),
    "Windows.Forensics.Prefetch": frozenset({"IncludeFilesAccessed", "dateAfter", "dateBefore", "hashRegex"}),
    "Windows.Forensics.RecentApps": frozenset({"UserFilter"}),
    "Windows.Forensics.SAM": frozenset(),
    "Windows.Forensics.Timeline": frozenset({"UserFilter", "Win10TimelineGlob"}),
    "Windows.Forensics.UEFI": frozenset({"DISABLE_DANGEROUS_API_CALLS", "SectorSize", "TargetGlob"}),
    "Windows.Forensics.Usn": frozenset({"AllDrives", "DateAfter", "DateBefore", "FileNameRegex", "MFT_ID_Regex", "Parent_MFT_ID_Regex"}),
    "Windows.KapeFiles.Remapping": frozenset(),
    "Windows.Memory.ProcessInfo": frozenset({"PidRegex", "ProcessNameRegex"}),
    "Windows.NTFS.MFT": frozenset(
        {"AllDrives", "AllNtfs", "DateAfter", "DateBefore", "FileRegex", "NTFS_INCLUDE_SHORT_NAMES", "SizeMax", "SizeMin"},
    ),
    "Windows.Network.ListeningPorts": frozenset(),
    "Windows.Network.Netstat": frozenset(),
    "Windows.Persistence.Debug": frozenset(),
    "Windows.Persistence.PermanentWMIEvents": frozenset({"AllRootNamespaces"}),
    "Windows.Persistence.Wow64cpu": frozenset(),
    "Windows.Registry.AppCompatCache": frozenset(),
    "Windows.Registry.BackupRestore": frozenset({"KeyGlob"}),
    "Windows.Registry.PortProxy": frozenset({"KeyGlob"}),
    "Windows.Registry.WDigest": frozenset({"ShowAllValues", "WDigestGlob"}),
    "Windows.Search.VSS": frozenset({"SearchFilesGlob", "VSS_MAX_AGE_DAYS"}),
    "Windows.Sys.AppcompatShims": frozenset({"customKeys", "shimKeys"}),
    "Windows.Sys.CertificateAuthorities": frozenset(),
    "Windows.Sys.DiskInfo": frozenset(),
    "Windows.Sys.Drivers": frozenset({"AlsoCheckAuthenticode", "DISABLE_DANGEROUS_API_CALLS"}),
    "Windows.Sys.FirewallRules": frozenset(),
    "Windows.Sys.PhysicalMemoryRanges": frozenset(),
    "Windows.Sys.Programs": frozenset({"programKeys"}),
    "Windows.System.CatFiles": frozenset({"SignerExcludeRegex", "SignerFilterRegex"}),
    "Windows.System.CriticalServices": frozenset(),
    "Windows.System.DLLs": frozenset(
        {"Calculate_Hash", "CertificateInfo", "DISABLE_DANGEROUS_API_CALLS", "DllRegex", "PidRegex", "ProcessRegex"},
    ),
    "Windows.System.DNSCache": frozenset(),
    "Windows.System.DomainRole": frozenset({"DomainRegex", "HostNameRegex", "RoleRegex"}),
    "Windows.System.Handles": frozenset({"Files", "IncludeAccessMasks", "Key", "processRegex"}),
    "Windows.System.HostsFile": frozenset({"HostnameRegex", "ResolutionRegex"}),
    "Windows.System.Powershell.ModuleAnalysisCache": frozenset({"FunctionNameRegex"}),
    "Windows.System.Pslist": frozenset(
        {"DISABLE_DANGEROUS_API_CALLS", "PidRegex", "ProcessRegex", "UntrustedAuthenticode", "UseTracker", "UsernameRegex"},
    ),
    "Windows.System.RootCAStore": frozenset(),
    "Windows.System.SVCHost": frozenset(),
    "Windows.System.Services": frozenset(
        {
            "Calculate_hashes",
            "CertificateInfo",
            "DISABLE_DANGEROUS_API_CALLS",
            "DisplayNameRegex",
            "NameRegex",
            "ServiceDllRegex",
            "servicesKeyGlob",
        },
    ),
    "Windows.System.Shares": frozenset({"NameRegex"}),
    "Windows.System.Signers": frozenset({"DISABLE_DANGEROUS_API_CALLS", "ShowAllSigners"}),
    "Windows.System.Threads": frozenset({"PidRegex", "ProcessRegex"}),
    "Windows.System.UntrustedBinaries": frozenset({"DISABLE_DANGEROUS_API_CALLS", "processNamesRegex"}),
    "Windows.Timeline.MFT": frozenset(
        {"AllocatedType", "DateAfter", "DateBefore", "EntryType", "Inode", "MFTFilename", "NameRegex", "SizeMax", "SizeMin"},
    ),
    "Windows.Timeline.Prefetch": frozenset({"dateAfter", "dateBefore", "hashRegex"}),
}

# Command, remediation and other response artifacts. Never analyst-collectable: a test keeps
# them off ANALYST_ARTIFACTS, and they are refused even if someone adds one there.
RESPONSE_ARTIFACTS = frozenset(
    {
        *(member.value for member in CommandArtifactsEnum),
        *(member.value for member in QuarantineArtifactsEnum),
        "Windows.Execute.RemotePowerShellScript",
        "Linux.Execute.RemoteBashScript",
        "Generic.Client.VQL",
        "Windows.System.VBScript",
        "Windows.Remediation.ScheduledTasks",
        "Windows.Remediation.Sinkhole",
        "Windows.Remediation.QuarantineMonitor",
        "MacOS.Remediation.Quarantine",
        "Windows.Network.NetstatEnriched",
        "Generic.Client.CleanupTemp",
        "Linux.Utils.InstallDeb",
        "Windows.Sysinternals.SysmonInstall",
        "Admin.Client.Uninstall",
    },
)


def is_response_role(user) -> bool:
    """True for the roles that may run response artifacts (admin, responder)."""
    try:
        return RoleEnum(user.role_id) in RESPONSE_ROLES
    except (ValueError, TypeError, AttributeError):
        return False


def response_artifacts() -> frozenset:
    """`RESPONSE_ARTIFACTS` plus the quarantine artifacts this deployment is configured to use."""
    from app.connectors.velociraptor.services.artifacts import (
        resolve_quarantine_artifact,
    )

    return RESPONSE_ARTIFACTS | {resolve_quarantine_artifact(member.value) for member in QuarantineArtifactsEnum}


def _definition_vql(definition: dict) -> str:
    parts = [definition.get("export"), definition.get("precondition")]
    for source in definition.get("sources") or []:
        if isinstance(source, dict):
            parts += [source.get("query"), source.get("precondition"), *(source.get("queries") or [])]
    return "\n".join(str(part) for part in parts if part)


def _vql_views(vql: str):
    """The VQL as scanned: as written and with comments removed, backticks dropped from both.

    vfilter accepts a backtick-quoted function name and comments between a name and its parenthesis; the
    comment-free view catches those. Comments are stripped without regard to string literals,
    which could hide a call that sits between a ``/*`` and ``*/`` inside two strings -- so the
    original text is scanned too.
    """
    without_comments = re.sub(r"(?s)/\*.*?\*/", " ", vql)
    without_comments = re.sub(r"(?m)^\s*(--|//).*$", " ", without_comments)
    return [view.replace("`", "") for view in (vql, without_comments)]


def is_shipped_definition(definition: dict) -> bool:
    """True when the org resolves the artifact to Velociraptor's compiled-in definition."""
    return definition.get("compiled_in") is True


def read_only_violation(definition: Optional[dict]) -> Optional[str]:
    """Why the definition does not look like a read-only collection (rule 4), or None."""
    if not definition:
        return "its definition was not found in the host's Velociraptor org"
    for field in ("required_permissions", "implied_permissions"):
        elevated = {str(p) for p in (definition.get(field) or [])} - READ_ONLY_PERMISSIONS
        if elevated:
            return f"its definition declares the permission(s) {', '.join(sorted(elevated))}"
    if definition.get("imports"):
        return "its definition imports other artifacts"
    if definition.get("tools"):
        return "its definition fetches tools"
    for vql in _vql_views(_definition_vql(definition)):
        call = _FORBIDDEN_CALL.search(vql)
        if call:
            return f"its definition calls {call.group(1)}()"
        for name in _ARTIFACT_REFERENCE.findall(vql):
            if name not in ANALYST_ARTIFACTS:
                return f"its definition calls Artifact.{name}, which analysts may not collect"
    return None


def definitions_violation(artifact_name: str, definitions: List[dict]) -> Optional[str]:
    """Why the artifact and its dependencies, as the host's org resolves them, may not run (rules 1, 2, 4)."""
    by_name = {str(definition.get("name")): definition for definition in definitions or [] if isinstance(definition, dict)}
    if artifact_name not in by_name:
        return "its definition was not found in the host's Velociraptor org"
    for name in [artifact_name] + sorted(set(by_name) - {artifact_name}):
        definition = by_name[name]
        subject = "its definition" if name == artifact_name else f"its dependency {name}"
        if name not in ANALYST_ARTIFACTS:
            return f"{subject} is not on the analyst artifact allowlist"
        if not is_shipped_definition(definition):
            return f"{subject} is not Velociraptor's built-in definition in the host's org"
        reason = read_only_violation(definition)
        if reason is not None:
            return reason if name == artifact_name else f"{subject}: {reason}"
    return None


def parameter_violation(artifact_name: str, definition: dict, requested: Optional[Dict[str, str]]) -> Optional[str]:
    """Why a requested parameter is not one an analyst may set (rule 2), or None."""
    safe = ANALYST_ARTIFACTS.get(artifact_name, frozenset())
    defaults = {
        str(param.get("name")): param.get("default")
        for param in (definition.get("parameters") or [])
        if isinstance(param, dict) and param.get("name") is not None
    }
    for name, value in (requested or {}).items():
        if name in safe:
            continue
        default = defaults.get(name)
        if name in defaults and isinstance(value, str) and vql_string_literal_value(value) == ("" if default is None else str(default)):
            continue
        return f"analysts may not set its parameter '{name}'"
    return None


def _refuse(user, artifact_name: str, reason: str):
    logger.warning(f"Refused /collect of {artifact_name} for user {getattr(user, 'username', '?')}: {reason}")
    raise HTTPException(status_code=403, detail=f"Artifact {artifact_name} can only be collected by an admin or responder: {reason}")


async def enforce_built_in_definitions(artifact_name: str, org_id: str) -> None:
    """Refuse (403) unless the artifact and every dependency resolve to Velociraptor's built-in
    definitions in `org_id` (rule 2 above, for everyone): a Talon collection, whose approver is an
    admin or responder and so isn't held to the analyst allowlist (``talon_catalogue``)."""
    from app.connectors.velociraptor.services.artifacts import (
        get_artifact_policy_definitions,
    )

    definitions = [d for d in await get_artifact_policy_definitions(artifact_name, org_id) if isinstance(d, dict)]
    names = {str(d.get("name")) for d in definitions}
    reason = None
    if artifact_name not in names:
        reason = "its definition was not found in the host's Velociraptor org"
    else:
        custom = sorted(str(d.get("name")) for d in definitions if not is_shipped_definition(d))
        if custom:
            reason = f"{', '.join(custom)} is not Velociraptor's built-in definition in the host's org"
    if reason is not None:
        logger.warning(f"Refused a Talon collection of {artifact_name}: {reason}")
        raise HTTPException(status_code=403, detail=f"Artifact {artifact_name} can't be collected for Talon: {reason}")


async def enforce_collect_artifact_policy(user, artifact_name: str, org_id: str, parameters=None) -> None:
    """Refuse (403) an analyst's /collect unless the allowlist admits the artifact and parameters.

    `org_id` is the host's Velociraptor org: the definition is read there, where the collection
    will run. `parameters` is the request's `parameters` field, in either accepted shape.
    """
    if is_response_role(user):
        return
    if artifact_name in response_artifacts():
        _refuse(user, artifact_name, "it is a command or remediation artifact")
    if artifact_name not in ANALYST_ARTIFACTS:
        _refuse(user, artifact_name, "it is not on the analyst artifact allowlist")

    from app.connectors.velociraptor.services.artifacts import (
        get_artifact_policy_definitions,
    )
    from app.connectors.velociraptor.services.artifacts import (
        requested_artifact_parameters,
    )

    definitions = await get_artifact_policy_definitions(artifact_name, org_id)
    reason = definitions_violation(artifact_name, definitions)
    if reason is None:
        definition = next(d for d in definitions if isinstance(d, dict) and d.get("name") == artifact_name)
        reason = parameter_violation(artifact_name, definition, requested_artifact_parameters(parameters))
    if reason is not None:
        _refuse(user, artifact_name, reason)
