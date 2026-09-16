import json
import re
from datetime import datetime
from datetime import timedelta
from typing import Any
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

from loguru import logger
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.wazuh_indexer.utils.universal import (
    create_wazuh_indexer_client_async,
)
from app.db.universal_models import Agents
from app.incidents.models import VeloSigmaExclusion
from app.incidents.schema.db_operations import AlertOut
from app.incidents.schema.db_operations import AlertTagCreate
from app.incidents.schema.db_operations import CommentCreate
from app.incidents.schema.incident_alert import CreateAlertRequest
from app.incidents.schema.incident_alert import CreatedAlertPayload
from app.incidents.schema.velo_sigma import DefenderEvent
from app.incidents.schema.velo_sigma import GenericEvent
from app.incidents.schema.velo_sigma import PowerShellEvent
from app.incidents.schema.velo_sigma import SysmonEvent
from app.incidents.schema.velo_sigma import VelociraptorSigmaAlert
from app.incidents.schema.velo_sigma import VelociraptorSigmaAlertResponse
from app.incidents.schema.velo_sigma import VeloSigmaExclusionCreate
from app.incidents.schema.velo_sigma import VeloSigmaExclusionDraft
from app.incidents.schema.velo_sigma import VeloSigmaExclusionDraftField
from app.incidents.schema.velo_sigma import VeloSigmaExclusionDryRunRequest
from app.incidents.schema.velo_sigma import VeloSigmaExclusionDryRunResponse
from app.incidents.services.db_operations import add_alert_tag_if_not_exists
from app.incidents.services.db_operations import create_comment
from app.incidents.services.incident_alert import create_alert
from app.incidents.services.incident_alert import create_alert_full

# ---------------------------------------------------------------------------
# Event-field extraction (shared by ingest-time matching, the draft builder and the dry-run)
# ---------------------------------------------------------------------------

# The comments `_create_copilot_alert` / `_create_fallback_alert` leave on the CoPilot alert are
# the only place the original Sigma payload survives, so in-context exclusion creation (#934)
# reads them back. Keep these prefixes in sync with the writers below.
SIGMA_META_COMMENT_PREFIX = "Velociraptor Sigma: "
SIGMA_FALLBACK_COMMENT_PREFIX = "Velociraptor Sigma Alert (No Wazuh match found)"
SIGMA_PAYLOAD_COMMENT_PREFIX = "Full Event Payload:"

# Fields worth pre-selecting as an exclusion key, most discriminating first. They are stable
# across repeated occurrences of the same benign activity, which is what an exclusion pins.
SUGGESTED_FIELD_PRIORITY: Tuple[str, ...] = (
    "Image",
    "SourceImage",
    "TargetImage",
    "CommandLine",
    "ParentImage",
    "ParentCommandLine",
    "TargetFilename",
    "TargetObject",
    "Path",
    "Process Name",
    "HostApplication",
    "ScriptBlockText",
    "DestinationHostname",
    "DestinationIp",
    "QueryName",
    "User",
    "SourceUser",
    "TargetUser",
    "Threat Name",
    "OriginalFileName",
    "Product",
    "Company",
)
MAX_SUGGESTED_FIELDS = 3

# Fields that differ on every event. Offered for completeness but never suggested, and flagged
# so the UI can warn that pinning one produces a rule that matches exactly once.
_VOLATILE_FIELD_PATTERN = re.compile(
    r"(guid|time|record|sequence|^.*id$|^.*ids$|hash|logon|checksum)",
    re.IGNORECASE,
)


def extract_event_fields(alert: VelociraptorSigmaAlert) -> Dict[str, str]:
    """Flatten the alert's ``EventData`` into the ``{name: value}`` map the exclusion matcher looks fields up in.

    This is the single definition of what an exclusion's ``field_matches`` key can refer to. The
    draft builder offers exactly these names, and the dry-run evaluates against exactly this map,
    so a rule created from an alert can only ever name fields the ingest-time check will find.
    Raises on an unparseable event; callers decide whether that means "skip" or "400".
    """
    parsed_event = alert.get_parsed_event()
    logger.debug(f"Extracting event fields | Channel: {alert.channel} | Type: {type(parsed_event).__name__}")
    event_data: Dict[str, str] = {}

    if hasattr(parsed_event, "EventData"):
        # First add all top-level fields
        for attr_name in dir(parsed_event.EventData):
            if not attr_name.startswith("_") and not callable(getattr(parsed_event.EventData, attr_name)):
                try:
                    value = getattr(parsed_event.EventData, attr_name)
                    if not callable(value):
                        event_data[attr_name] = str(value)
                except Exception:
                    pass

        # Special handling for PowerShell ContextInfo which contains Host Application
        if hasattr(parsed_event.EventData, "ContextInfo") and parsed_event.EventData.ContextInfo:
            # Parse the ContextInfo string which contains multiple lines of key-value pairs
            context_info = parsed_event.EventData.ContextInfo
            logger.debug(f"Found ContextInfo in PowerShell event: {context_info}")

            for line in context_info.splitlines():
                line = line.strip()
                if line and " = " in line:
                    key, value = line.split(" = ", 1)
                    key = key.strip()
                    # Add these fields with their original names for direct matching
                    event_data[key] = value.strip()
                    # Also add common CamelCase variations to make matching more flexible
                    if " " in key:
                        # Convert "Host Application" to "HostApplication"
                        camel_key = "".join(word.capitalize() for word in key.split())
                        camel_key = camel_key[0].lower() + camel_key[1:]  # lowerCamelCase
                        event_data[camel_key] = value.strip()

    # Pydantic models expose their config too - it is not an event field.
    event_data.pop("model_config", None)
    event_data.pop("model_fields", None)
    event_data.pop("model_computed_fields", None)
    event_data.pop("model_extra", None)
    event_data.pop("model_fields_set", None)
    return event_data


def parse_sigma_comments(comments: Iterable[str]) -> Tuple[Optional[str], Optional[str], Optional[Dict[str, Any]]]:
    """Recover ``(title, channel, event)`` from the comments the Sigma ingest wrote on a CoPilot alert.

    Handles both writers: the Wazuh-matched path (``Velociraptor Sigma: <title> | <channel>``) and
    the fallback path (a multi-line ``Title:`` / ``Channel:`` block). Any part that cannot be
    recovered comes back as ``None`` rather than raising - a stored alert is never invalid, just
    incomplete.
    """
    title: Optional[str] = None
    channel: Optional[str] = None
    event: Optional[Dict[str, Any]] = None

    for raw in comments:
        text = (raw or "").strip()
        if not text:
            continue

        if text.startswith(SIGMA_META_COMMENT_PREFIX) and title is None:
            meta = text[len(SIGMA_META_COMMENT_PREFIX) :].strip()
            # The channel never contains " | " while a Sigma title might, so split from the right.
            if " | " in meta:
                title, channel = (part.strip() for part in meta.rsplit(" | ", 1))
            else:
                title = meta
            continue

        if text.startswith(SIGMA_FALLBACK_COMMENT_PREFIX) and title is None:
            for line in text.splitlines():
                key, sep, value = line.partition(":")
                if not sep:
                    continue
                key = key.strip().lower()
                if key == "title":
                    title = value.strip() or None
                elif key == "channel":
                    channel = value.strip() or None
            continue

        if text.startswith(SIGMA_PAYLOAD_COMMENT_PREFIX) and event is None:
            body = text[len(SIGMA_PAYLOAD_COMMENT_PREFIX) :].strip()
            # The payload is fenced: ```\n{...}\n```
            if body.startswith("```"):
                body = body[3:]
                if body.endswith("```"):
                    body = body[:-3]
            body = body.strip()
            try:
                parsed = json.loads(body)
            except json.JSONDecodeError:
                logger.warning("Sigma payload comment is not valid JSON; ignoring it")
                continue
            if isinstance(parsed, dict):
                event = parsed

    return title, channel, event


def sigma_alert_from_copilot_alert(alert: AlertOut) -> Optional[VelociraptorSigmaAlert]:
    """Rebuild the inbound ``VelociraptorSigmaAlert`` from a stored CoPilot alert, or ``None`` if it was not one.

    Only the parts the exclusion matcher reads are faithful (``channel``, ``title``, ``event``,
    ``computer``, ``clientID``); ``level`` / ``index_pattern`` / ``sourceRef`` are placeholders.

    An alert that kept its meta comment but lost the payload one (seen in the wild: the payload
    write is best-effort at ingest) still comes back, with an empty ``event`` - channel and title
    are enough to draft a rule, just not to offer field candidates. ``has_event_payload`` tells
    the two apart.
    """
    title, channel, event = parse_sigma_comments(c.comment for c in alert.comments)
    if event is None and title is None and channel is None:
        return None

    event = event or {}
    system = event.get("System") if isinstance(event.get("System"), dict) else {}
    if channel is None and isinstance(system.get("Channel"), str):
        channel = system["Channel"]

    asset = alert.assets[0] if alert.assets else None
    computer = (system.get("Computer") if isinstance(system.get("Computer"), str) else None) or (asset.asset_name if asset else None)

    return VelociraptorSigmaAlert(
        computer=computer or "unknown",
        clientID=asset.velociraptor_id if asset else None,
        channel=channel or "",
        title=title or "",
        level="unknown",
        event=event,
        index_pattern="n/a",
        sourceRef=str(alert.id),
    )


def has_event_payload(alert: VelociraptorSigmaAlert) -> bool:
    return bool(alert.event)


def _is_volatile_field(name: str) -> bool:
    return bool(_VOLATILE_FIELD_PATTERN.search(name))


def build_exclusion_draft(alert: AlertOut) -> Optional[VeloSigmaExclusionDraft]:
    """Turn a stored Sigma alert into a pre-filled exclusion rule, or ``None`` if the payload is gone."""
    sigma_alert = sigma_alert_from_copilot_alert(alert)
    if sigma_alert is None:
        return None

    event_fields: Dict[str, str] = {}
    if has_event_payload(sigma_alert):
        try:
            event_fields = extract_event_fields(sigma_alert)
        except Exception as e:  # the stored payload can predate a schema change
            logger.warning(f"Could not extract event fields for alert {alert.id}: {e}")

    priority = {name: rank for rank, name in enumerate(SUGGESTED_FIELD_PRIORITY)}
    suggested_left = MAX_SUGGESTED_FIELDS
    fields: List[VeloSigmaExclusionDraftField] = []
    for name in sorted(event_fields, key=lambda n: (priority.get(n, len(priority)), n.lower())):
        value = event_fields[name]
        if value in ("", "None"):
            continue
        volatile = _is_volatile_field(name)
        suggested = name in priority and not volatile and suggested_left > 0
        if suggested:
            suggested_left -= 1
        fields.append(VeloSigmaExclusionDraftField(name=name, value=value, suggested=suggested, volatile=volatile))

    title = sigma_alert.title or None
    channel = sigma_alert.channel or None
    computer = sigma_alert.computer if sigma_alert.computer != "unknown" else None

    name = f"Exclude: {title}" if title else f"Exclusion from alert #{alert.id}"
    where = f" on {computer}" if computer else ""
    description = f"False positive observed on alert #{alert.id}{where}. Justification: "

    return VeloSigmaExclusionDraft(
        alert_id=alert.id,
        customer_code=alert.customer_code or None,
        channel=channel,
        title=title,
        computer=computer,
        name=name[:255],
        description=description,
        payload_available=has_event_payload(sigma_alert),
        fields=fields,
    )


class VeloSigmaExclusionService:
    """Service for managing and checking Velociraptor Sigma exclusions."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def check_exclusions(self, alert: VelociraptorSigmaAlert) -> Optional[VeloSigmaExclusion]:
        """
        Check if the given alert matches any exclusion rules.

        Args:
            alert: The Velociraptor Sigma alert to check

        Returns:
            The first matching exclusion rule, or None if no match is found
        """
        # Get all enabled exclusions
        stmt = select(VeloSigmaExclusion).where(VeloSigmaExclusion.enabled == True)
        result = await self.session.execute(stmt)
        exclusions = result.scalars().all()

        if not exclusions:
            return None

        # Parse the event data
        try:
            event_data = extract_event_fields(alert)
            for key, value in event_data.items():
                logger.debug(f"Extracted field: {key} = {value}")
        except Exception as e:
            logger.error(f"Error parsing event data: {str(e)}")
            # If we can't parse the event, we won't exclude it
            return None

        # Resolve the tenant once; customer-scoped rules compare against it.
        customer_code = await self.resolve_customer_code(alert)

        # Check each exclusion against this alert
        for exclusion in exclusions:
            logger.debug(f"Checking exclusion: {exclusion.name} (ID: {exclusion.id})")
            if await self._matches_exclusion(alert, event_data, exclusion, customer_code):
                # Update match statistics
                await self._update_exclusion_stats(exclusion.id)
                return exclusion

        return None

    async def _matches_exclusion(
        self,
        alert: VelociraptorSigmaAlert,
        event_data: Dict[str, str],
        exclusion: VeloSigmaExclusion,
        customer_code: Optional[str] = None,
    ) -> bool:
        """Check if the alert matches the given exclusion rule.

        ``customer_code`` is the tenant the alert was resolved to (see ``resolve_customer_code``);
        ``None`` means it could not be resolved, in which case a customer-scoped rule never matches.
        """
        # Check customer code if specified
        if exclusion.customer_code and exclusion.customer_code != customer_code:
            logger.debug(f"Customer code mismatch: rule={exclusion.customer_code}, alert={customer_code}")
            return False

        # Check channel if specified
        if exclusion.channel and exclusion.channel != alert.channel:
            logger.debug(f"Channel mismatch: rule={exclusion.channel}, alert={alert.channel}")
            return False

        # Check title if specified
        if exclusion.title and exclusion.title != alert.title:
            logger.debug(f"Title mismatch: rule={exclusion.title}, alert={alert.title}")
            return False

        # Check field matches if specified
        if exclusion.field_matches:
            for field_name, field_value in exclusion.field_matches.items():
                # Special handling for Host Application field
                if field_name.lower() == "hostapplication" and field_name not in event_data:
                    # Try common variations
                    alternate_keys = ["Host Application", "HostApplication", "hostApplication"]
                    found = False
                    for alt_key in alternate_keys:
                        if alt_key in event_data:
                            field_name = alt_key  # Use the key that exists in the data
                            found = True
                            break
                    if not found:
                        logger.debug(f"Field '{field_name}' and its variations not found in event data")
                        return False

                # Direct match
                if field_name in event_data:
                    event_value = event_data[field_name]
                    logger.debug(f"Checking field match: {field_name}={field_value} against {event_value}")

                    # Support exact match or regex match
                    if isinstance(field_value, str):
                        if field_value.startswith("regex:"):
                            # Remove the regex: prefix and try to match
                            regex_pattern = field_value[6:]
                            # Special handling for path-based regex patterns
                            if (
                                "path" in field_name.lower()
                                or "file" in field_name.lower()
                                or "\\" in regex_pattern
                                or "/" in regex_pattern
                            ):
                                try:
                                    # Normalize paths for comparison by converting all to lowercase and standardizing backslashes
                                    pattern = regex_pattern.lower().replace("\\\\", "\\")
                                    value = event_value.lower().replace("\\\\", "\\")

                                    # Remove the regex: prefix if present
                                    if pattern.startswith("regex:"):
                                        pattern = pattern[6:]

                                    # Handle escaped parentheses in Windows paths
                                    pattern = pattern.replace("\\(", "(").replace("\\)", ")")

                                    # Convert the wildcard pattern to proper regex format
                                    # Escape special regex characters except for the wildcards we want to keep
                                    pattern_parts = re.split(r"(\.\*)", pattern)
                                    regex_parts = []

                                    for i, part in enumerate(pattern_parts):
                                        if part == ".*":
                                            # Keep wildcards as-is
                                            regex_parts.append(part)
                                        else:
                                            # Escape regex special characters but keep path separators
                                            escaped = re.escape(part)
                                            regex_parts.append(escaped)

                                    pattern_regex = "".join(regex_parts)

                                    # Force matching the entire string
                                    pattern_regex = f"^{pattern_regex}$"

                                    logger.debug(f"Path regex check: Pattern='{pattern}' → Regex='{pattern_regex}' vs Value='{value}'")

                                    # Try the match
                                    match_result = re.search(pattern_regex, value, re.IGNORECASE)
                                    if match_result:
                                        logger.debug(f"Path regex match succeeded! Match: {match_result.group(0)}")
                                        return True
                                    else:
                                        logger.debug("Path regex match failed")
                                        return False

                                except Exception as e:
                                    logger.error(f"Error in path regex matching: {str(e)}")
                                    return False
                            else:
                                # Standard regex for non-path values
                                try:
                                    if not re.search(regex_pattern, event_value, re.IGNORECASE):
                                        logger.debug(f"Regex pattern '{regex_pattern}' did not match '{event_value}'")
                                        return False
                                    else:
                                        logger.debug(f"Regex pattern '{regex_pattern}' matched '{event_value}'")
                                except re.error as e:
                                    logger.error(f"Invalid regex pattern in exclusion {exclusion.id}: {regex_pattern} - Error: {str(e)}")
                                    return False
                        else:
                            # Case-insensitive path comparison for Windows paths
                            if "path" in field_name.lower() or "file" in field_name.lower() or "\\" in field_value or "/" in field_value:
                                # Log raw values for debugging
                                logger.debug(f"Before normalization - Rule: '{field_value}', Event: '{event_value}'")

                                # Use the path normalization helper
                                norm_field_value = self._normalize_windows_path(field_value)
                                norm_event_value = self._normalize_windows_path(event_value)

                                logger.debug(f"After normalization - Rule: '{norm_field_value}', Event: '{norm_event_value}'")

                                if norm_field_value != norm_event_value:
                                    logger.debug(f"Path mismatch: rule='{norm_field_value}' event='{norm_event_value}'")
                                    return False
                                else:
                                    logger.debug(f"Path match found for: {field_name}")
                            else:
                                # Standard case-insensitive match for other fields
                                if field_value.lower() != event_value.lower():
                                    logger.debug(f"Case-insensitive match failed: rule='{field_value}' event='{event_value}'")
                                    return False
                    else:
                        # For non-string values (like lists or objects), convert to string for comparison
                        if str(field_value) != event_value:
                            logger.debug(f"String conversion match failed: rule='{str(field_value)}' event='{event_value}'")
                            return False
                else:
                    # If field doesn't exist in the event and we're looking for it, no match
                    logger.debug(f"Field '{field_name}' not found in event data")
                    logger.debug(f"Available fields: {', '.join(event_data.keys())}")
                    return False

        # If we passed all checks, this is a match
        logger.info(f"Alert matched exclusion rule '{exclusion.name}' (ID: {exclusion.id})")
        return True

    def _normalize_windows_path(self, path: str, is_regex: bool = False) -> str:
        """
        Normalize Windows paths by converting all backslash variations to a consistent format.

        Args:
            path: The path string to normalize
            is_regex: Whether the path contains regex patterns that should be preserved

        Returns:
            Normalized path with consistent backslashes and formatting
        """
        if not path:
            return ""

        # Convert to lowercase for case-insensitive comparison
        normalized = path.lower()

        if is_regex:
            # Special handling for regex patterns
            # First, temporarily replace regex character classes with placeholders
            placeholders = {}

            # Find all character classes like [^\\] or [\\w] and preserve them
            char_class_pattern = r"(\[\^?[^\]]*\])"
            char_classes = re.finditer(char_class_pattern, normalized)

            for i, match in enumerate(char_classes):
                placeholder = f"__REGEX_PLACEHOLDER_{i}__"
                placeholders[placeholder] = match.group(0)
                normalized = normalized.replace(match.group(0), placeholder)

        # Use regex to replace any sequence of one or more backslashes with a single backslash
        # This handles \, \\, \\\, \\\\, etc.
        normalized = re.sub(r"\\+", r"\\", normalized)

        # Handle escaped special characters in paths
        normalized = normalized.replace("\\(", "(").replace("\\)", ")")
        normalized = normalized.replace("\\[", "[").replace("\\]", "]")
        normalized = normalized.replace("\\ ", " ")

        # Remove any trailing backslash
        if normalized.endswith("\\"):
            normalized = normalized[:-1]

        if is_regex:
            # Restore the regex character classes with their original content
            for placeholder, original in placeholders.items():
                normalized = normalized.replace(placeholder, original)

        # Log only in debug for excessive paths
        if path != normalized:
            path_preview = path[:20] + "..." if len(path) > 20 else path
            norm_preview = normalized[:20] + "..." if len(normalized) > 20 else normalized
            logger.debug(f"Path normalized: '{path_preview}' → '{norm_preview}'")

        return normalized

    async def _update_exclusion_stats(self, exclusion_id: int) -> None:
        """Update the statistics for an exclusion after it matches."""
        try:
            stmt = (
                update(VeloSigmaExclusion)
                .where(VeloSigmaExclusion.id == exclusion_id)
                .values(last_matched_at=datetime.utcnow(), match_count=VeloSigmaExclusion.match_count + 1)
            )
            await self.session.execute(stmt)
            await self.session.commit()
        except Exception as e:
            logger.error(f"Error updating exclusion stats: {str(e)}")
            # Don't raise the error, just log it

    async def resolve_customer_code(self, alert: VelociraptorSigmaAlert) -> Optional[str]:
        """Resolve the tenant of an inbound Sigma alert through the ``agents`` table.

        Tries the Velociraptor client id first, then the hostname - the same keys the alert
        creation path uses. Returns ``None`` when neither is enrolled, which makes every
        customer-scoped rule a non-match (fail closed) while deployment-wide rules still apply.

        Before this existed the check compared against a hard-coded ``"unknown"``, so a rule with
        a customer code could never match anything - exactly what the Sources form produced by
        default, since it pre-fills the customer from the global filter.
        """
        try:
            if alert.clientID:
                result = await self.session.execute(select(Agents.customer_code).where(Agents.velociraptor_id == alert.clientID))
                code = result.scalar_one_or_none()
                if code:
                    return code
            if alert.computer:
                result = await self.session.execute(select(Agents.customer_code).where(Agents.hostname == alert.computer))
                code = result.scalars().first()
                if code:
                    return code
        except Exception as e:
            logger.error(f"Error resolving customer code for Sigma alert: {str(e)}")
        logger.debug(f"Could not resolve a customer code for computer={alert.computer!r} clientID={alert.clientID!r}")
        return None

    async def dry_run(self, alert: AlertOut, rule: VeloSigmaExclusionDryRunRequest) -> VeloSigmaExclusionDryRunResponse:
        """Evaluate an unsaved rule against the stored alert it is being created from - no DB, no side effects.

        Uses the same ``_matches_exclusion`` the ingest path runs, so "matches" here means the
        next identical alert would be suppressed. When it does not match, each failing criterion
        is named so the analyst can see which exact-match field is off.
        """
        sigma_alert = sigma_alert_from_copilot_alert(alert)
        if sigma_alert is None:
            return VeloSigmaExclusionDryRunResponse(
                success=True,
                message="This alert carries no Velociraptor Sigma payload; nothing to test against",
                matches=False,
                reasons=["Alert has no Velociraptor Sigma event payload"],
            )

        event_data: Dict[str, str] = {}
        if has_event_payload(sigma_alert):
            try:
                event_data = extract_event_fields(sigma_alert)
            except Exception as e:
                return VeloSigmaExclusionDryRunResponse(
                    success=True,
                    message="The stored event payload could not be parsed",
                    matches=False,
                    reasons=[f"Event payload could not be parsed: {e}"],
                )

        customer_code = alert.customer_code or None
        candidate = VeloSigmaExclusion(
            name="dry-run",
            created_by="dry-run",
            channel=rule.channel or None,
            title=rule.title or None,
            field_matches=rule.field_matches or None,
            customer_code=rule.customer_code or None,
        )
        if await self._matches_exclusion(sigma_alert, event_data, candidate, customer_code):
            return VeloSigmaExclusionDryRunResponse(success=True, message="The rule matches the originating alert", matches=True)

        # Isolate which criteria fail so the UI can point at them.
        reasons: List[str] = []
        if candidate.customer_code and candidate.customer_code != customer_code:
            reasons.append(f"Customer mismatch: rule={candidate.customer_code!r}, alert={customer_code!r}")
        if candidate.channel and candidate.channel != sigma_alert.channel:
            reasons.append(f"Channel mismatch: rule={candidate.channel!r}, alert={sigma_alert.channel!r}")
        if candidate.title and candidate.title != sigma_alert.title:
            reasons.append(f"Title mismatch: rule={candidate.title!r}, alert={sigma_alert.title!r}")
        if candidate.field_matches and not has_event_payload(sigma_alert):
            reasons.append("Alert stores no event payload, so field matches cannot be verified against it")
        for field_name, field_value in (candidate.field_matches or {}).items():
            if not has_event_payload(sigma_alert):
                break
            single = VeloSigmaExclusion(name="dry-run", created_by="dry-run", field_matches={field_name: field_value})
            if not await self._matches_exclusion(sigma_alert, event_data, single, customer_code):
                if field_name not in event_data and field_name.lower() != "hostapplication":
                    reasons.append(f"Field {field_name!r} is not present on the alert event")
                else:
                    reasons.append(f"Field {field_name!r} does not match: rule={field_value!r}, alert={event_data.get(field_name)!r}")
        if not reasons:
            reasons.append("The rule does not match the originating alert")

        return VeloSigmaExclusionDryRunResponse(
            success=True,
            message="The rule would NOT have suppressed the originating alert",
            matches=False,
            reasons=reasons,
        )

    async def create_exclusion(self, exclusion: VeloSigmaExclusionCreate) -> VeloSigmaExclusion:
        """Create a new exclusion rule."""
        exclusion_data = exclusion.model_dump()

        # Ensure created_by is set to something non-null
        if not exclusion_data.get("created_by"):
            exclusion_data["created_by"] = "system"  # Default fallback

        db_exclusion = VeloSigmaExclusion(**exclusion_data)
        self.session.add(db_exclusion)
        await self.session.commit()
        await self.session.refresh(db_exclusion)
        return db_exclusion

    async def get_exclusion(self, exclusion_id: int) -> Optional[VeloSigmaExclusion]:
        """Retrieve an exclusion by ID."""
        stmt = select(VeloSigmaExclusion).where(VeloSigmaExclusion.id == exclusion_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_exclusions(self, skip: int = 0, limit: int = 100, enabled_only: bool = False) -> List[VeloSigmaExclusion]:
        """List all exclusion rules with pagination."""
        query = select(VeloSigmaExclusion)
        if enabled_only:
            query = query.where(VeloSigmaExclusion.enabled == True)
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def update_exclusion(self, exclusion_id: int, exclusion_data: Dict[str, Any]) -> Optional[VeloSigmaExclusion]:
        """Update an existing exclusion rule."""
        db_exclusion = await self.get_exclusion(exclusion_id)
        if not db_exclusion:
            return None

        # Update only provided fields
        for key, value in exclusion_data.items():
            if hasattr(db_exclusion, key):
                setattr(db_exclusion, key, value)

        await self.session.commit()
        await self.session.refresh(db_exclusion)
        return db_exclusion

    async def delete_exclusion(self, exclusion_id: int) -> bool:
        """Delete an exclusion rule."""
        db_exclusion = await self.get_exclusion(exclusion_id)
        if not db_exclusion:
            return False

        await self.session.delete(db_exclusion)
        await self.session.commit()
        return True

    async def list_exclusions_with_count(self, skip: int = 0, limit: int = 100, enabled_only: bool = False) -> tuple[list, int]:
        """
        List all exclusion rules with pagination and return total count.

        Args:
            skip: Number of items to skip
            limit: Maximum number of items to return
            enabled_only: If True, only return enabled exclusions

        Returns:
            Tuple of (list of exclusions, total count)
        """
        query = select(VeloSigmaExclusion)

        if enabled_only:
            query = query.where(VeloSigmaExclusion.enabled == True)

        # Get total count first
        count_query = select(func.count()).select_from(query.subquery())
        # Change self.db to self.session
        total_count = await self.session.scalar(count_query)

        # Then get the paginated results
        query = query.order_by(VeloSigmaExclusion.id.desc())
        query = query.offset(skip).limit(limit)

        # Change self.db to self.session
        result = await self.session.execute(query)
        exclusions = result.scalars().all()

        return list(exclusions), total_count


class VelociraptorSigmaService:
    """Service for handling Velociraptor Sigma alerts and their integration with Wazuh."""

    def __init__(self, session: AsyncSession):
        """Initialize with a database session."""
        self.session = session

    async def _create_fallback_alert(self, alert: VelociraptorSigmaAlert, result: Dict[str, Any]) -> None:
        """
        Create a fallback alert when no matching Wazuh event is found.
        Uses create_alert_full to generate an alert directly from the Velociraptor data.
        """
        try:
            # Extract timestamp from the event if available
            timestamp = None
            parsed_event = alert.get_parsed_event()
            if hasattr(parsed_event, "System") and hasattr(parsed_event.System, "TimeCreated"):
                timestamp = datetime.fromtimestamp(parsed_event.System.TimeCreated.SystemTime).isoformat()
            else:
                timestamp = datetime.utcnow().isoformat()

            # Extract event information for context
            event_context = {}
            if hasattr(parsed_event, "EventData"):
                # Try to convert EventData to dict for context
                try:
                    event_context = parsed_event.EventData.model_dump()
                except AttributeError:
                    # If not directly convertible, extract key attributes
                    event_context = {
                        "event_record_id": getattr(parsed_event.System, "EventRecordID", "Unknown"),
                        "channel": getattr(parsed_event.System, "Channel", "Unknown"),
                        "computer": getattr(parsed_event.System, "Computer", "Unknown"),
                    }

            # Add alert metadata to context
            event_context.update(
                {
                    "alert_title": alert.title,
                    "alert_level": alert.level,
                    "alert_channel": alert.channel,
                    "alert_source": alert.source,
                    "computer": alert.computer,
                    "clientID": alert.clientID,
                },
            )

            # Create a unique ID for this alert based on sourceRef and timestamp - Not using for now
            # unique_id = f"{alert.sourceRef}_{int(datetime.utcnow().timestamp())}"

            # Look up the customer code from Agents table using the clientID
            customer_code = "not_found"  # Default fallback
            if alert.clientID:
                # Query the Agents table to find matching agent by velociraptor_id
                agent_query = select(Agents).where(Agents.velociraptor_id == alert.clientID)
                agent_result = await self.session.execute(agent_query)
                agent = agent_result.scalar_one_or_none()

                if agent and agent.customer_code:
                    logger.info(f"Found agent details {agent}")
                    customer_code = agent.customer_code
                    # ! SOMETIMES VELOCIRAPTOR AND WAZUH ENUMERATE DIFFERENT HOSTNAMES ! #
                    # ! Due to this, we will use the agent.hostname as the asset name as this is what ! #
                    # ! used in the Wazuh events.!#
                    agent_name = agent.hostname
                    logger.info(f"Found customer code '{customer_code}' for clientID {alert.clientID}")
                else:
                    logger.warning(f"No agent found with velociraptor_id '{alert.clientID}', using default customer code")
            else:
                logger.warning("No clientID provided in the alert, using default customer code")

            # Create the alert using create_alert_full
            alert_id = await create_alert_full(
                alert_payload=CreatedAlertPayload(
                    alert_context_payload=event_context,
                    asset_payload=agent_name,
                    timefield_payload=timestamp,
                    alert_title_payload=alert.title,
                    source=alert.source,
                    index_id="not_applicable",
                    index_name="not_applicable",
                ),
                customer_code=customer_code,  # Use the looked up customer code
                session=self.session,
                threshold_alert=False,
                velo_sigma_alert=True,
            )
            result["alert_id"] = alert_id

            # Add a comment with more context
            event_type = type(parsed_event).__name__
            await create_comment(
                comment=CommentCreate(
                    alert_id=result["alert_id"],
                    comment=(
                        f"Velociraptor Sigma Alert (No Wazuh match found)\n"
                        f"Title: {alert.title}\n"
                        f"Channel: {alert.channel}\n"
                        f"Level: {alert.level}\n"
                        f"Computer: {alert.computer}\n"
                        f"Event Type: {event_type}\n"
                        f"Event Record ID: {result.get('event_record_id', 'Unknown')}\n"
                        f"Customer Code: {customer_code}\n"
                    ),
                    user_name="admin",
                    created_at=datetime.utcnow(),
                ),
                db=self.session,
            )

            # Add the full event payload as a separate comment
            try:
                # Convert event to string if it's an object or dictionary
                event_payload = alert.event
                if not isinstance(event_payload, str):
                    # Try to serialize using json
                    try:
                        event_payload = json.dumps(
                            event_payload,
                            default=lambda o: o.__dict__ if hasattr(o, "__dict__") else str(o),
                            indent=2,
                        )
                    except TypeError:
                        # If JSON serialization fails, use string representation
                        event_payload = str(event_payload)

                await create_comment(
                    comment=CommentCreate(
                        alert_id=result["alert_id"],
                        comment=f"Full Event Payload:\n```\n{event_payload}\n```",
                        user_name="admin",
                        created_at=datetime.utcnow(),
                    ),
                    db=self.session,
                )
                logger.info(f"Added full event payload as comment to alert ID: {result['alert_id']}")
            except Exception as e:
                logger.error(f"Failed to add event payload as comment: {str(e)}")
                logger.exception(e)

            # Add tags
            await add_alert_tag_if_not_exists(alert_tag=AlertTagCreate(alert_id=result["alert_id"], tag=f"{alert.type}"), db=self.session)
            await add_alert_tag_if_not_exists(
                alert_tag=AlertTagCreate(alert_id=result["alert_id"], tag="velociraptor-direct"),
                db=self.session,
            )

            # Add event-specific tags
            if "Sysmon" in alert.channel:
                await add_alert_tag_if_not_exists(
                    alert_tag=AlertTagCreate(alert_id=result["alert_id"], tag="event_type:sysmon"),
                    db=self.session,
                )
            elif "Defender" in alert.channel:
                await add_alert_tag_if_not_exists(
                    alert_tag=AlertTagCreate(alert_id=result["alert_id"], tag="event_type:defender"),
                    db=self.session,
                )
            elif "PowerShell" in alert.channel:
                await add_alert_tag_if_not_exists(
                    alert_tag=AlertTagCreate(alert_id=result["alert_id"], tag="event_type:powershell"),
                    db=self.session,
                )
            else:
                # Generic event type
                await add_alert_tag_if_not_exists(
                    alert_tag=AlertTagCreate(alert_id=result["alert_id"], tag="event_type:generic"),
                    db=self.session,
                )

            logger.info(f"Created fallback CoPilot alert with ID: {result['alert_id']} for customer {customer_code}")
            result["success"] = True

        except Exception as e:
            logger.error(f"Failed to create fallback CoPilot alert: {str(e)}")
            logger.exception(e)
            result["alert_id"] = None
            result["success"] = False
            result["reason"] = f"Failed to create fallback alert: {str(e)}"

    async def process_alert(self, alert: VelociraptorSigmaAlert) -> VelociraptorSigmaAlertResponse:
        """
        Process a Velociraptor Sigma alert and create a corresponding CoPilot alert.

        Args:
            alert: The Velociraptor Sigma alert to process

        Returns:
            Response indicating the success or failure of the processing
        """
        try:
            # Check exclusions first
            exclusion_service = VeloSigmaExclusionService(self.session)
            matching_exclusion = await exclusion_service.check_exclusions(alert)

            if matching_exclusion:
                # Alert is excluded, return a response indicating this
                logger.info(f"Skipping alert processing: matched exclusion rule '{matching_exclusion.name}' (ID: {matching_exclusion.id})")
                return VelociraptorSigmaAlertResponse(
                    success=True,
                    message=f"Alert excluded by rule: {matching_exclusion.name}",
                    alert_id=None,
                    excluded=True,
                    exclusion_id=matching_exclusion.id,
                )

            # Parse event and determine event type
            result = await self._process_event_by_type(alert)

            # Create an alert in CoPilot if the processing was successful
            if result.get("success"):
                await self._create_copilot_alert(alert, result)
            else:
                # If no Wazuh alert was found, try to create a fallback alert
                logger.info("No matching Wazuh alert found, creating fallback alert...")
                await self._create_fallback_alert(alert, result)

            # Build response
            return self._build_response(alert, result)

        except Exception as e:
            logger.error(f"Error processing Velociraptor Sigma alert: {str(e)}")
            logger.exception(e)
            return VelociraptorSigmaAlertResponse(success=False, message=f"Error: {str(e)}", alert_id=getattr(alert, "sourceRef", None))

    async def _process_event_by_type(self, alert: VelociraptorSigmaAlert) -> Dict[str, Any]:
        """Process event according to its type or channel."""
        parsed_event = alert.get_parsed_event()
        logger.debug(f"Processing alert | Channel: {alert.channel} | Type: {type(parsed_event).__name__}")

        # Use type checking and channel fallback
        if isinstance(parsed_event, SysmonEvent):
            return await self._process_sysmon_event(alert, parsed_event)
        elif isinstance(parsed_event, DefenderEvent):
            return await self._process_defender_event(alert, parsed_event)
        elif "Sysmon" in alert.channel:
            logger.warning(f"Expected SysmonEvent but got {type(parsed_event).__name__} for Sysmon channel")
            return await self._process_sysmon_event(alert, parsed_event)
        elif "Defender" in alert.channel:
            logger.warning(f"Expected DefenderEvent but got {type(parsed_event).__name__} for Defender channel")
            return await self._process_defender_event(alert, parsed_event)
        elif "PowerShell" in alert.channel:
            logger.warning(f"Expected PowerShellEvent but got {type(parsed_event).__name__} for PowerShell channel")
            return await self._process_powershell_event(alert, parsed_event)
        else:
            # Use a generic processor for unknown event types
            logger.info(f"Using generic processor for channel: {alert.channel}")
            return await self._process_generic_event(alert, parsed_event)

    async def _process_sysmon_event(self, alert: VelociraptorSigmaAlert, parsed_event: Union[SysmonEvent, GenericEvent]) -> Dict[str, Any]:
        """Process a Sysmon event."""
        logger.info(f"Processing Sysmon event from channel: {alert.channel}")

        try:
            # Extract key fields safely
            event_record_id = str(parsed_event.System.EventRecordID)

            # Safely access EventData fields with fallbacks
            event_data = parsed_event.EventData
            rule_name = getattr(event_data, "RuleName", "Unknown Rule")
            source_image = getattr(event_data, "SourceImage", "Unknown Source")
            target_image = getattr(event_data, "TargetImage", "Unknown Target")
            source_process_id = getattr(event_data, "SourceProcessId", 0)
            source_user = getattr(event_data, "SourceUser", "Unknown User")

            agent_name = alert.computer  # Default to the computer name from the alert

            if alert.clientID:
                # Query the Agents table to find matching agent by velociraptor_id
                agent_query = select(Agents).where(Agents.velociraptor_id == alert.clientID)
                agent_result = await self.session.execute(agent_query)
                agent = agent_result.scalar_one_or_none()

                if agent and agent.hostname:
                    logger.info(f"Found agent details {agent}")
                    # ! SOMETIMES VELOCIRAPTOR AND WAZUH ENUMERATE DIFFERENT HOSTNAMES ! #
                    # ! Due to this, we will use the agent.hostname as the asset name as this is what ! #
                    # ! used in the Wazuh events.!#
                    agent_name = agent.hostname

            # Fetch corresponding Wazuh alert
            wazuh_event = await self._fetch_wazuh_alert(
                agent_name=agent_name,
                event_record_id=event_record_id,
                index_pattern=alert.index_pattern,
            )

            # Build result
            result = {
                "event_record_id": event_record_id,
                "rule_name": rule_name,
                "source_image": source_image,
                "target_image": target_image,
                "source_process_id": source_process_id,
                "source_user": source_user,
                "wazuh_data": wazuh_event,
                "success": wazuh_event is not None,
            }

            logger.info(f"Sysmon event processed | EventRecordID: {event_record_id} | Success: {result['success']}")
            return result

        except AttributeError as e:
            logger.error(f"Failed to process Sysmon event - missing attribute: {str(e)}")
            return {"success": False, "reason": f"Failed to process Sysmon event: {str(e)}"}

    async def _process_defender_event(
        self,
        alert: VelociraptorSigmaAlert,
        parsed_event: Union[DefenderEvent, GenericEvent],
    ) -> Dict[str, Any]:
        """Process a Windows Defender event."""
        logger.info(f"Processing Defender event from channel: {alert.channel}")

        try:
            # Extract event record ID
            event_record_id = str(parsed_event.System.EventRecordID)

            agent_name = alert.computer  # Default to the computer name from the alert

            if alert.clientID:
                # Query the Agents table to find matching agent by velociraptor_id
                agent_query = select(Agents).where(Agents.velociraptor_id == alert.clientID)
                agent_result = await self.session.execute(agent_query)
                agent = agent_result.scalar_one_or_none()

                if agent and agent.hostname:
                    logger.info(f"Found agent details {agent}")
                    # ! SOMETIMES VELOCIRAPTOR AND WAZUH ENUMERATE DIFFERENT HOSTNAMES ! #
                    # ! Due to this, we will use the agent.hostname as the asset name as this is what ! #
                    # ! used in the Wazuh events.!#
                    agent_name = agent.hostname

            # Fetch corresponding Wazuh alert
            wazuh_event = await self._fetch_wazuh_alert(
                agent_name=agent_name,
                event_record_id=event_record_id,
                index_pattern=alert.index_pattern,
            )

            # Build basic result
            result = {"event_record_id": event_record_id, "wazuh_data": wazuh_event, "success": wazuh_event is not None}

            # Safely extract additional fields
            event_data = parsed_event.EventData

            if hasattr(event_data, "product_name"):
                result["product_name"] = event_data.product_name

            if hasattr(event_data, "threat_name"):
                result["threat_name"] = event_data.threat_name

            if hasattr(event_data, "severity_name"):
                result["severity"] = event_data.severity_name

            logger.info(f"Defender event processed | EventRecordID: {event_record_id} | Success: {result['success']}")
            return result

        except AttributeError as e:
            logger.error(f"Failed to process Defender event - missing attribute: {str(e)}")
            return {"success": False, "reason": f"Failed to process Defender event: {str(e)}"}

    async def _process_powershell_event(
        self,
        alert: VelociraptorSigmaAlert,
        parsed_event: Union[PowerShellEvent, GenericEvent],
    ) -> Dict[str, Any]:
        """Process a PowerShell event."""
        logger.info(f"Processing PowerShell event from channel: {alert.channel}")

        try:
            # Extract event record ID
            event_record_id = str(parsed_event.System.EventRecordID)

            agent_name = alert.computer  # Default to the computer name from the alert

            if alert.clientID:
                # Query the Agents table to find matching agent by velociraptor_id
                agent_query = select(Agents).where(Agents.velociraptor_id == alert.clientID)
                agent_result = await self.session.execute(agent_query)
                agent = agent_result.scalar_one_or_none()

                if agent and agent.hostname:
                    logger.info(f"Found agent details {agent}")
                    # ! SOMETIMES VELOCIRAPTOR AND WAZUH ENUMERATE DIFFERENT HOSTNAMES ! #
                    # ! Due to this, we will use the agent.hostname as the asset name as this is what ! #
                    # ! used in the Wazuh events.!#
                    agent_name = agent.hostname

            # Fetch corresponding Wazuh alert
            wazuh_event = await self._fetch_wazuh_alert(
                agent_name=agent_name,
                event_record_id=event_record_id,
                index_pattern=alert.index_pattern,
            )

            # Build basic result
            result = {"event_record_id": event_record_id, "wazuh_data": wazuh_event, "success": wazuh_event is not None}

            # Safely extract PowerShell specific fields
            event_data = parsed_event.EventData

            # Add ScriptBlock details if available
            if hasattr(event_data, "ScriptBlockText"):
                result["script_block_text"] = event_data.ScriptBlockText
                # Store only first 100 chars as a preview to avoid overwhelming logs
                preview = event_data.ScriptBlockText[:100] + "..." if len(event_data.ScriptBlockText) > 100 else event_data.ScriptBlockText
                result["script_preview"] = preview

            if hasattr(event_data, "ScriptBlockId"):
                result["script_block_id"] = event_data.ScriptBlockId

            if hasattr(event_data, "MessageNumber") and hasattr(event_data, "MessageTotal"):
                result["message_part"] = f"{event_data.MessageNumber} of {event_data.MessageTotal}"

            # Add host information if available
            if hasattr(event_data, "HostApplication"):
                result["host_application"] = event_data.HostApplication

            if hasattr(event_data, "CommandName"):
                result["command_name"] = event_data.CommandName

            logger.info(f"PowerShell event processed | EventRecordID: {event_record_id} | Success: {result['success']}")
            return result

        except AttributeError as e:
            logger.error(f"Failed to process PowerShell event - missing attribute: {str(e)}")
            return {"success": False, "reason": f"Failed to process PowerShell event: {str(e)}"}

    async def _process_generic_event(self, alert: VelociraptorSigmaAlert, parsed_event: GenericEvent) -> Dict[str, Any]:
        """Process a generic event that doesn't match known types."""
        logger.info(f"Processing generic event from channel: {alert.channel}")

        try:
            # Extract event record ID if available
            event_record_id = str(getattr(parsed_event.System, "EventRecordID", "unknown"))

            agent_name = alert.computer  # Default to the computer name from the alert

            if alert.clientID:
                # Query the Agents table to find matching agent by velociraptor_id
                agent_query = select(Agents).where(Agents.velociraptor_id == alert.clientID)
                agent_result = await self.session.execute(agent_query)
                agent = agent_result.scalar_one_or_none()

                if agent and agent.hostname:
                    logger.info(f"Found agent details {agent}")
                    # ! SOMETIMES VELOCIRAPTOR AND WAZUH ENUMERATE DIFFERENT HOSTNAMES ! #
                    # ! Due to this, we will use the agent.hostname as the asset name as this is what ! #
                    # ! used in the Wazuh events.!#
                    agent_name = agent.hostname

            # Try to fetch corresponding Wazuh alert if we have an event record ID
            wazuh_event = None
            if event_record_id != "unknown":
                wazuh_event = await self._fetch_wazuh_alert(
                    agent_name=agent_name,
                    event_record_id=event_record_id,
                    index_pattern=alert.index_pattern,
                )

            # Build basic result
            result = {
                "event_record_id": event_record_id,
                "wazuh_data": wazuh_event,
                "success": wazuh_event is not None,
                "channel": alert.channel,
            }

            # Extract some generic system info
            if hasattr(parsed_event, "System"):
                system = parsed_event.System
                if hasattr(system, "Channel"):
                    result["system_channel"] = system.Channel
                if hasattr(system, "Provider") and hasattr(system.Provider, "Name"):
                    result["provider_name"] = system.Provider.Name
                if hasattr(system, "EventID") and hasattr(system.EventID, "Value"):
                    result["event_id"] = system.EventID.Value

            # Try to extract some event data if available
            if hasattr(parsed_event, "EventData"):
                try:
                    # Add the first few items from EventData to the result
                    event_data = parsed_event.EventData
                    event_data_dict = {}

                    # Get all attributes that aren't methods or private
                    for attr_name in dir(event_data):
                        if not attr_name.startswith("_") and not callable(getattr(event_data, attr_name)):
                            try:
                                value = getattr(event_data, attr_name)
                                if not callable(value):  # Skip methods
                                    event_data_dict[attr_name] = str(value)
                            except Exception as attr_error:
                                logger.warning(f"Failed to access attribute '{attr_name}': {str(attr_error)}")
                                # Skip attributes that can't be accessed
                                pass

                    # Add to result, limited to prevent overwhelming logs
                    result["event_data"] = {k: v for i, (k, v) in enumerate(event_data_dict.items()) if i < 10}

                except Exception as e:
                    logger.warning(f"Failed to extract event data details: {e}")

            logger.info(f"Generic event processed | EventRecordID: {event_record_id} | Success: {result['success']}")
            return result

        except Exception as e:
            logger.error(f"Failed to process generic event: {str(e)}")
            logger.exception(e)
            return {"success": False, "reason": f"Failed to process generic event: {str(e)}"}

    async def _create_copilot_alert(self, alert: VelociraptorSigmaAlert, result: Dict[str, Any]) -> None:
        """Create an alert in CoPilot with comments and tags."""
        try:
            # Create the alert
            wazuh_data = result["wazuh_data"]
            alert_response = await create_alert(
                alert=CreateAlertRequest(index_name=wazuh_data["index_name"], alert_id=wazuh_data["alert_id"]),
                session=self.session,
            )
            result["alert_id"] = alert_response

            # Add a comment
            await create_comment(
                comment=CommentCreate(
                    alert_id=result["alert_id"],
                    comment=f"Velociraptor Sigma: {alert.title} | {alert.channel}",
                    user_name="admin",
                    created_at=datetime.utcnow(),
                ),
                db=self.session,
            )

            # Add the full event payload as a separate comment
            try:
                # Convert event to string if it's an object or dictionary
                event_payload = alert.event
                if not isinstance(event_payload, str):
                    # Try to serialize using json
                    try:
                        event_payload = json.dumps(
                            event_payload,
                            default=lambda o: o.__dict__ if hasattr(o, "__dict__") else str(o),
                            indent=2,
                        )
                    except TypeError:
                        # If JSON serialization fails, use string representation
                        event_payload = str(event_payload)

                await create_comment(
                    comment=CommentCreate(
                        alert_id=result["alert_id"],
                        comment=f"Full Event Payload:\n```\n{event_payload}\n```",
                        user_name="admin",
                        created_at=datetime.utcnow(),
                    ),
                    db=self.session,
                )
                logger.info(f"Added full event payload as comment to alert ID: {result['alert_id']}")
            except Exception as e:
                logger.error(f"Failed to add event payload as comment: {str(e)}")
                logger.exception(e)

            # Add a tag
            await add_alert_tag_if_not_exists(alert_tag=AlertTagCreate(alert_id=result["alert_id"], tag=f"{alert.type}"), db=self.session)

            logger.info(f"Created CoPilot alert with ID: {result['alert_id']}")

        except Exception as e:
            logger.error(f"Failed to create CoPilot alert: {str(e)}")
            logger.exception(e)
            result["alert_id"] = None

    def _build_response(self, alert: VelociraptorSigmaAlert, result: Dict[str, Any]) -> VelociraptorSigmaAlertResponse:
        """Build the response based on processing results."""
        success = result.get("success", False)

        if not success:
            message = f"Failed to process {alert.channel} alert: {result.get('reason', 'Unknown error')}"
            logger.warning(f"{message} | EventRecordID: {result.get('event_record_id', 'Unknown')}")
        else:
            message = f"Successfully processed {alert.channel} alert"
            logger.info(f"{message} | EventRecordID: {result.get('event_record_id')} | AlertID: {result.get('alert_id')}")

        return VelociraptorSigmaAlertResponse(success=success, message=message, alert_id=result.get("alert_id"))

    async def _fetch_wazuh_alert(self, agent_name: str, event_record_id: str, index_pattern: str) -> Optional[Dict[str, Any]]:
        """Fetch alert data from Wazuh Indexer."""
        try:
            # Create client and prepare search parameters
            client = await create_wazuh_indexer_client_async("Wazuh-Indexer")

            # Use ISO format for timestamps to avoid format errors - default to current time -1 hour
            # This is to ensure we are searching within the last hour
            # ! Might need to revisit this if the time window is too small ! #
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            timestamp = one_hour_ago.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

            # Build query
            query = self._build_wazuh_query(agent_name, event_record_id, timestamp)
            logger.debug(f"Searching Wazuh Indexer | Query: {query}")

            # Execute search
            response = await self._execute_wazuh_search(client, query, index_pattern)

            # Extract and return results
            return self._extract_wazuh_results(response)

        except Exception as e:
            logger.error(f"Error fetching alert data: {str(e)}")
            logger.exception(e)
            return None

    @staticmethod
    def _build_wazuh_query(agent_name: str, event_record_id: str, timestamp: str) -> Dict[str, Any]:
        """Build the OpenSearch query for finding the alert in Wazuh."""
        return {
            "bool": {
                "must": [{"term": {"agent_name": agent_name}}, {"term": {"data_win_system_eventRecordID": event_record_id}}],
                "filter": [{"range": {"timestamp": {"gte": timestamp}}}],
            },
        }

    @staticmethod
    async def _execute_wazuh_search(client, query: Dict[str, Any], index_pattern: str) -> Dict[str, Any]:
        """Execute the search against the Wazuh Indexer."""
        try:
            response = await client.search(index=index_pattern, body={"query": query}, size=1, timeout="1m")
            logger.debug(f"Search response received | Status: {'hits' in response}")
            return response
        except Exception as search_error:
            logger.error(f"Search operation failed: {str(search_error)}")
            logger.exception(search_error)
            return {}

    @staticmethod
    def _extract_wazuh_results(response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract the alert data from the Wazuh Indexer response."""
        if not response or "hits" not in response or "hits" not in response["hits"]:
            logger.warning("Invalid response structure from Wazuh Indexer")
            return None

        hits = response["hits"]["hits"]
        if not hits:
            logger.warning("No matching alerts found in Wazuh Indexer")
            return None

        # Get the first matching hit
        hit = hits[0]

        # Extract index, document ID and source data
        index_name = hit.get("_index")
        alert_id = hit.get("_id")
        raw_alert = hit.get("_source", {})

        # Enrich the raw alert with metadata needed for references
        raw_alert["index_name"] = index_name
        raw_alert["alert_id"] = alert_id

        logger.debug(f"Successfully extracted raw alert data from index {index_name} with ID {alert_id}")
        return raw_alert


async def create_velo_sigma_alert(alert: VelociraptorSigmaAlert, session: AsyncSession) -> VelociraptorSigmaAlertResponse:
    """Process a Velociraptor Sigma alert using the VelociraptorSigmaService."""
    service = VelociraptorSigmaService(session)
    return await service.process_alert(alert)
