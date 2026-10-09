"""Editing the aws-s3 wodle in the Wazuh manager's `ossec.conf`.

One `<wodle name="aws-s3">` holds every customer's sources as `<bucket>` entries, the same shape as
Office365's one `<office365>` block holding several `<api_auth>` blocks. Provisioning reconciles one
instance's buckets inside that wodle (creating the wodle when it is absent) and decommissioning
removes only that instance's buckets, dropping the wodle when nothing is left in it.

Everything here is a pure string-in, string-out transformation so it can be tested without a
manager. Two things differ deliberately from the Office365 code:

* The configuration is never written to disk: it carries every customer's credentials.
* It tolerates several `<ossec_config>` blocks and keeps comments. The raw file is parsed under a
  synthetic root and serialized back block by block, so the push does not strip every comment an
  engineer left in the file.

An instance's buckets are recognised by bucket name + AWS account ID. Provisioning refuses an
account that another instance already uses with the same bucket, so that pair is unique to one
instance deployment-wide.
"""

import copy
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from dataclasses import field
from typing import Dict
from typing import List
from typing import Set
from typing import Tuple

from app.integrations.aws.schema.provision import ProvisionAwsAuthKeys
from app.integrations.aws.utils.services import AwsServiceConfig

WODLE_NAME = "aws-s3"

# Applied only when CoPilot creates the wodle; an existing wodle's settings are left as they are.
WODLE_DEFAULTS = (
    ("disabled", "no"),
    ("interval", "10m"),
    ("run_on_start", "yes"),
    ("skip_on_error", "yes"),
)

_WRAPPER_TAG = "copilot_ossec_wrapper"
_XML_DECLARATION = re.compile(r"^\s*<\?xml[^>]*\?>")
_DTD = re.compile(r"<!(DOCTYPE|ENTITY)", re.IGNORECASE)


class AwsWazuhConfigError(ValueError):
    """The configuration cannot be edited safely; the message is fit to show the operator."""


@dataclass
class ReconcileResult:
    config: str
    changed: bool
    added: List[str] = field(default_factory=list)
    updated: List[str] = field(default_factory=list)
    removed: List[str] = field(default_factory=list)
    wodle_created: bool = False
    wodle_removed: bool = False
    wodle_disabled: bool = False
    # Copies of the instance's buckets as they were before this change — what a rollback restores.
    previous: List[ET.Element] = field(default_factory=list)


# ---------------------------------------------------------------------------------------------
# Parsing and serialization
# ---------------------------------------------------------------------------------------------


def parse_ossec_config(raw: str) -> ET.Element:
    """
    Parse the raw manager configuration under a synthetic root, keeping comments.

    A DTD is refused outright: ossec.conf never has one, and refusing it removes entity expansion
    (XXE, "billion laughs") from what the stdlib parser has to defend against.
    """
    if not raw or not raw.strip():
        raise AwsWazuhConfigError("The Wazuh manager returned an empty ossec.conf; refusing to edit it.")
    if _DTD.search(raw):
        raise AwsWazuhConfigError("The Wazuh manager's ossec.conf contains a DOCTYPE or ENTITY declaration; refusing to edit it.")
    body = _XML_DECLARATION.sub("", raw, count=1)
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
    try:
        parser.feed(f"<{_WRAPPER_TAG}>{body}</{_WRAPPER_TAG}>")
        wrapper = parser.close()
    except ET.ParseError as e:
        raise AwsWazuhConfigError(f"Could not parse the Wazuh manager's ossec.conf: {e}")
    if wrapper.find("ossec_config") is None:
        raise AwsWazuhConfigError("The Wazuh manager's configuration has no <ossec_config> block.")
    return wrapper


# What the Wazuh API substitutes for a secret it will not show (`wazuh.rbac.decorators.MASK_DEFAULT`).
WAZUH_MASK = "*****"


def _refuse_masked(wrapper: ET.Element) -> None:
    """
    Refuse a configuration in which the manager masked a value.

    Wazuh 4.14 masks secrets only in the JSON form of the configuration, never in the raw file
    CoPilot reads — but if a later version masks the raw form too, writing it back would replace
    every masked secret on the manager with asterisks.
    """
    for element in wrapper.iter():
        if isinstance(element.tag, str) and (element.text or "").strip() == WAZUH_MASK:
            raise AwsWazuhConfigError(
                f"The Wazuh manager returned ossec.conf with a masked value (<{element.tag}>{WAZUH_MASK}</{element.tag}>). "
                "Writing it back would destroy that value, so nothing was changed. Check the Wazuh API user's "
                "manager:update_config permission.",
            )


def serialize_ossec_config(wrapper: ET.Element) -> str:
    """The inverse of :func:`parse_ossec_config`: every top-level node back to back, tails included."""
    return (wrapper.text or "") + "".join(ET.tostring(child, encoding="unicode") for child in wrapper)


def _canonical(element: ET.Element) -> str:
    return ET.canonicalize(ET.tostring(element, encoding="unicode"), strip_text=True)


# ---------------------------------------------------------------------------------------------
# Buckets
# ---------------------------------------------------------------------------------------------


def build_bucket(
    config: AwsServiceConfig,
    keys: ProvisionAwsAuthKeys,
    only_logs_after: str,
) -> ET.Element:
    """
    The `<bucket>` element for one service of one AWS account.

    Credentials are written inline as `<access_key>` / `<secret_key>`. Wazuh documents these as
    deprecated since 4.4, but its 4.14 wodle still honours them (`WazuhIntegration.get_client` only
    prints a deprecation notice) and they are the only option CoPilot can manage end to end: the
    Wazuh API edits `ossec.conf` but cannot write `/root/.aws/credentials`, which an `aws_profile`
    would need. This is the one function that writes credentials, so moving to `aws_profile` later
    means replacing the two key elements here with one `<aws_profile>`.

    Never written: `<remove_from_bucket>` (the integration is read-only) and `<regions>` on
    CloudTrail (global-service events are logged under us-east-1 and a region filter drops them).
    `<aws_account_id>` is written for every service: without it the wodle lists every account under
    `AWSLogs/`, which on a shared or organization bucket would collect other customers' logs.
    """
    definition = config.definition
    bucket = ET.Element("bucket", {"type": definition.wazuh_type})
    ET.SubElement(bucket, "name").text = keys.BUCKET_NAME
    if config.prefix:
        ET.SubElement(bucket, "path").text = config.prefix
    ET.SubElement(bucket, "access_key").text = keys.ACCESS_KEY_ID
    ET.SubElement(bucket, "secret_key").text = keys.SECRET_ACCESS_KEY.get_secret_value()
    ET.SubElement(bucket, "aws_account_id").text = keys.AWS_ACCOUNT_ID
    if keys.AWS_ACCOUNT_ALIAS:
        ET.SubElement(bucket, "aws_account_alias").text = keys.AWS_ACCOUNT_ALIAS
    if keys.AWS_ORGANIZATION_ID and definition.supports_organization_id:
        ET.SubElement(bucket, "aws_organization_id").text = keys.AWS_ORGANIZATION_ID
    ET.SubElement(bucket, "only_logs_after").text = only_logs_after
    return bucket


def desired_buckets(keys: ProvisionAwsAuthKeys) -> List[ET.Element]:
    only_logs_after = keys.only_logs_after()
    return [build_bucket(config, keys, only_logs_after) for config in keys.service_configs()]


def _text(element: ET.Element, tag: str) -> str:
    return (element.findtext(tag) or "").strip()


def _bucket_type(bucket: ET.Element) -> str:
    return (bucket.get("type") or "").strip().lower()


def _bucket_path(bucket: ET.Element) -> str:
    return _text(bucket, "path").strip("/")


def _bucket_accounts(bucket: ET.Element) -> Set[str]:
    return {account.strip() for account in _text(bucket, "aws_account_id").split(",") if account.strip()}


def _describe(bucket: ET.Element) -> str:
    path = _bucket_path(bucket)
    accounts = ",".join(sorted(_bucket_accounts(bucket))) or "any account"
    return f"{_bucket_type(bucket) or 'untyped'} bucket {_text(bucket, 'name')}{'/' + path if path else ''} ({accounts})"


def is_owned_bucket(bucket: ET.Element, bucket_name: str, account_id: str) -> bool:
    """Whether a `<bucket>` belongs to the instance identified by bucket name + account."""
    return _text(bucket, "name") == bucket_name and _bucket_accounts(bucket) == {account_id}


def _overlaps(existing: ET.Element, desired: ET.Element, account_id: str) -> bool:
    """
    Whether an existing bucket would collect the same logs as a desired one.

    Same type, bucket and path, and either the same account or no account at all — a bucket entry
    without `<aws_account_id>` reads every account under `AWSLogs/`, ours included.
    """
    if _bucket_type(existing) != _bucket_type(desired):
        return False
    if _text(existing, "name") != _text(desired, "name") or _bucket_path(existing) != _bucket_path(desired):
        return False
    accounts = _bucket_accounts(existing)
    return not accounts or account_id in accounts


# ---------------------------------------------------------------------------------------------
# Reconcile
# ---------------------------------------------------------------------------------------------


def _aws_wodles(wrapper: ET.Element) -> List[tuple]:
    """Every `(ossec_config, wodle)` pair for the aws-s3 wodle, in document order."""
    return [
        (block, wodle)
        for block in wrapper.findall("ossec_config")
        for wodle in block.findall("wodle")
        if (wodle.get("name") or "").strip() == WODLE_NAME
    ]


def _new_wodle(block: ET.Element) -> ET.Element:
    wodle = ET.SubElement(block, "wodle", {"name": WODLE_NAME})
    for tag, value in WODLE_DEFAULTS:
        ET.SubElement(wodle, tag).text = value
    # Keep the closing `</ossec_config>` on its own line.
    previous = list(block)[-2] if len(block) > 1 else None
    if previous is not None and not (previous.tail or "").strip():
        previous.tail = "\n\n  "
    wodle.tail = "\n"
    return wodle


def _remove_keeping_layout(parent: ET.Element, child: ET.Element) -> None:
    """Remove ``child``, handing its trailing whitespace to whatever came before it."""
    children = list(parent)
    index = children.index(child)
    if index > 0:
        children[index - 1].tail = child.tail
    else:
        parent.text = child.tail
    parent.remove(child)


def _is_empty_wodle(wodle: ET.Element) -> bool:
    # A wodle with neither buckets nor services (CloudWatch Logs, Inspector, …) would only ever
    # log "No AWS buckets, services or subscribers defined" and exit.
    return not any(child.tag in ("bucket", "service", "subscriber") for child in wodle)


def reconcile_aws_buckets(
    raw_config: str,
    desired: List[ET.Element],
    bucket_name: str,
    account_id: str,
    adopt_existing: bool,
    keep_only_logs_after: bool = True,
) -> ReconcileResult:
    """
    Make one instance's buckets in the aws-s3 wodle exactly ``desired``; touch nothing else.

    - ``adopt_existing`` is True when the instance is already deployed: its buckets in the wodle are
      its own, so they are updated (key rotation) or removed (service dropped from `SERVICES`).
      On a first deployment it is False, and a bucket already collecting this account from this
      bucket — typically one an engineer configured by hand — is refused rather than silently
      taken over or duplicated.
    - Any *other* bucket that would collect the same logs is refused too: the manager would read
      every log twice.
    - ``keep_only_logs_after`` keeps an updated bucket's existing `only_logs_after` when the operator
      did not set one, so a re-sync does not move the start date to today.
    - ``desired=[]`` with ``adopt_existing=True`` removes the instance; the wodle goes when empty.

    Raises :class:`AwsWazuhConfigError` on a conflict, with every conflicting bucket named.
    """
    wrapper = parse_ossec_config(raw_config)
    _refuse_masked(wrapper)
    before = _canonical(wrapper)
    result = ReconcileResult(config=raw_config, changed=False)

    wodles = _aws_wodles(wrapper)
    existing = [(wodle, bucket) for _, wodle in wodles for bucket in wodle.findall("bucket")]

    owned = [(w, b) for w, b in existing if adopt_existing and is_owned_bucket(b, bucket_name, account_id)]
    owned_ids = {id(b) for _, b in owned}
    result.previous = [copy.deepcopy(b) for _, b in owned]
    conflicts = sorted(
        {
            _describe(bucket)
            for _, bucket in existing
            if id(bucket) not in owned_ids and any(_overlaps(bucket, want, account_id) for want in desired)
        },
    )
    if conflicts:
        raise AwsWazuhConfigError(
            "The Wazuh manager already collects these logs: "
            + "; ".join(conflicts)
            + ". Remove the existing <bucket> entries from the aws-s3 wodle in ossec.conf (or delete the CoPilot "
            "integration that owns them) and deploy again.",
        )

    owned_by_type: Dict[str, List[Tuple[ET.Element, ET.Element]]] = {}
    for wodle, bucket in owned:
        owned_by_type.setdefault(_bucket_type(bucket), []).append((wodle, bucket))

    if desired and not wodles:
        target_wodle = _new_wodle(wrapper.find("ossec_config"))
        result.wodle_created = True
    else:
        target_wodle = wodles[0][1] if wodles else None

    touched = set()
    leftovers: List[Tuple[ET.Element, ET.Element]] = []
    for want in desired:
        service = _bucket_type(want)
        matches = owned_by_type.pop(service, [])
        if not matches:
            target_wodle.append(copy.deepcopy(want))
            result.added.append(service)
            touched.add(id(target_wodle))
            continue

        wodle, current = matches[0]
        # A second owned bucket of the same type can only be a hand-made duplicate; it goes.
        leftovers.extend(matches[1:])
        replacement = copy.deepcopy(want)
        current_start = _text(current, "only_logs_after")
        if keep_only_logs_after and current_start:
            replacement.find("only_logs_after").text = current_start
        if _canonical(current) != _canonical(replacement):
            wodle.insert(list(wodle).index(current), replacement)
            wodle.remove(current)
            result.updated.append(service)
            touched.add(id(wodle))

    # Services dropped from `SERVICES` (or the whole instance, when `desired` is empty).
    for matches in owned_by_type.values():
        leftovers.extend(matches)
    for wodle, bucket in leftovers:
        wodle.remove(bucket)
        result.removed.append(_bucket_type(bucket))
        touched.add(id(wodle))

    for block, wodle in _aws_wodles(wrapper):
        if id(wodle) in touched and _is_empty_wodle(wodle):
            _remove_keeping_layout(block, wodle)
            result.wodle_removed = True
        elif id(wodle) in touched:
            ET.indent(wodle, space="  ", level=1)

    if target_wodle is not None:
        result.wodle_disabled = _text(target_wodle, "disabled").lower() == "yes"

    if _canonical(wrapper) != before:
        result.config = serialize_ossec_config(wrapper)
        result.changed = True
        verify_only_instance_changed(raw_config, result.config, bucket_name, account_id)
    return result


def owned_buckets(raw_config: str, bucket_name: str, account_id: str) -> List[ET.Element]:
    """Copies of the instance's current buckets — what a rollback restores."""
    wrapper = parse_ossec_config(raw_config)
    return [
        copy.deepcopy(bucket)
        for _, wodle in _aws_wodles(wrapper)
        for bucket in wodle.findall("bucket")
        if is_owned_bucket(bucket, bucket_name, account_id)
    ]


# ---------------------------------------------------------------------------------------------
# The safety net: prove a change touches nothing but this instance
# ---------------------------------------------------------------------------------------------


def _without_instance(raw: str, bucket_name: str, account_id: str) -> str:
    """
    The configuration with this instance's buckets taken out, in canonical form (comments kept,
    whitespace ignored). An aws-s3 wodle left with nothing but its settings is dropped too, since
    creating or removing it around this instance's buckets is part of the change.
    """
    wrapper = parse_ossec_config(raw)
    for block, wodle in _aws_wodles(wrapper):
        for bucket in wodle.findall("bucket"):
            if is_owned_bucket(bucket, bucket_name, account_id):
                wodle.remove(bucket)
        if _is_empty_wodle(wodle):
            block.remove(wodle)
    return ET.canonicalize(ET.tostring(wrapper, encoding="unicode"), with_comments=True, strip_text=True)


def verify_only_instance_changed(before: str, after: str, bucket_name: str, account_id: str) -> None:
    """
    Refuse to push a configuration that differs from the manager's in anything but this instance.

    Independent of how `reconcile_aws_buckets` got there: both files are parsed afresh, this
    instance's `<bucket>` entries are taken out of each, and what is left — every other block, other
    customers' buckets, the wodle's settings, comments — must be identical. A bug in the edit, or a
    serializer that lost something, then fails here instead of overwriting the manager's ossec.conf.
    """
    if _without_instance(before, bucket_name, account_id) != _without_instance(after, bucket_name, account_id):
        raise AwsWazuhConfigError(
            "Refusing to update ossec.conf: the new configuration would change more than this AWS instance's <bucket> "
            "entries. Nothing was written to the Wazuh manager.",
        )
