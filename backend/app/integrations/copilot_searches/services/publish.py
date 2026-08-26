"""Publish a detection rule to a client's own GitHub repo (their custom repo).

Writes the rule YAML straight to the customer's configured custom repo via the
GitHub Contents API (a direct commit to the configured branch). The write token
comes from the per-tenant MinIO config (see custom_repos) and is never exposed.

Feature-local: no shared-app changes. Rules live in the client's GitHub, not a
CoPilot DB — this is the write counterpart to RulesCache's read.
"""
from __future__ import annotations

import base64
import re
from typing import Any
from typing import Dict
from typing import Optional

import httpx
import yaml
from loguru import logger

from app.integrations.copilot_searches.services.copilot_searches import rules_cache
from app.integrations.copilot_searches.services.custom_repos import get_custom_repo
from app.integrations.copilot_searches.services.rule_linter import lint_result

GITHUB_API = "https://api.github.com"

# Publishes are constrained to detection YAMLs — never arbitrary repo paths
# (a write token must not be usable to overwrite READMEs, workflows, etc.).
_PATH_RE = re.compile(r"^detections/[A-Za-z0-9_\-][A-Za-z0-9_\-./]*\.ya?ml$")


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (name or "rule").lower()).strip("-")
    return s or "rule"


def _default_path(name: str) -> str:
    return f"detections/custom/{_slug(name)}.yaml"


def _gh_message(resp: httpx.Response) -> str:
    try:
        return resp.json().get("message", resp.text)
    except ValueError:
        return resp.text


async def publish_rule(
    rule_yaml: str,
    customer_code: str,
    message: Optional[str] = None,
    path: Optional[str] = None,
) -> Dict[str, Any]:
    """Commit a rule to the customer's custom GitHub repo. Returns a result dict."""

    def err(msg: str, **extra: Any) -> Dict[str, Any]:
        return {"success": False, "message": msg, "error": msg, **extra}

    # --- parse + validate the rule ---------------------------------------
    try:
        data = yaml.safe_load(rule_yaml)
    except yaml.YAMLError as exc:
        return err(f"Rule YAML is not parseable: {exc}")
    if not isinstance(data, dict):
        return err("Rule must be a YAML mapping.")
    name = str(data.get("name") or "").strip()
    if not name:
        return err("Rule has no name.")

    lint = lint_result(rule_yaml)
    if not lint.get("valid"):
        return err(
            f"Rule has {lint.get('error_count', 0)} validation error(s) — fix them before publishing.",
            findings=lint.get("findings", []),
        )

    # --- resolve the tenant's custom repo + write token ------------------
    if not customer_code:
        return err("Select a customer to publish to.")
    cfg = await get_custom_repo(customer_code)
    if not cfg or not cfg.get("repo"):
        return err(f"Customer '{customer_code}' has no custom repository configured. Add one under Custom repos first.")
    token = cfg.get("token")
    if not token:
        return err(
            f"The custom repo for '{customer_code}' has no write token. "
            "Add a GitHub PAT with 'contents:write' in Custom repos to publish.",
        )
    repo = cfg["repo"]
    branch = cfg.get("branch") or "main"
    target_path = (path or "").strip() or _default_path(name)
    if "\\" in target_path or ".." in target_path or not _PATH_RE.match(target_path):
        return err(
            "path must be a YAML file under detections/ "
            "(e.g. detections/custom/my-rule.yaml) — no '..', backslashes, or other locations.",
        )

    # --- id collision: a rule id must be unique across catalog + all custom repos.
    # Re-publishing the SAME rule to the SAME file is an update and is allowed;
    # anything else would be silently dropped by the cache on refresh (first wins).
    rule_id = str(data.get("id") or "").strip()
    existing = None
    if rule_id:
        try:
            await rules_cache.ensure_loaded()
            existing = rules_cache.get_rule_by_id(rule_id)
        except Exception as exc:  # noqa: BLE001 — cache trouble must not block publishing
            logger.warning(f"[publish] id-collision check skipped (cache unavailable): {exc}")
    if existing is not None:
        same_file = (
            existing.get("_provenance") == "custom"
            and existing.get("_owner_customer_code") == customer_code
            and existing.get("_file_path") == target_path
        )
        if not same_file:
            where = (
                "the shared catalog"
                if existing.get("_provenance") != "custom"
                else f"'{existing.get('_file_path')}' (customer {existing.get('_owner_customer_code')})"
            )
            return err(
                f"Rule id {rule_id} is already used by '{existing.get('name')}' in {where}. "
                "Give this rule a new UUID (or publish to that rule's existing path to update it).",
            )

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    content_b64 = base64.b64encode(rule_yaml.encode("utf-8")).decode("ascii")

    try:
        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            # existing file? need its sha to update
            get_resp = await client.get(f"{GITHUB_API}/repos/{repo}/contents/{target_path}", params={"ref": branch})
            sha: Optional[str] = None
            if get_resp.status_code == 200:
                sha = get_resp.json().get("sha")
            elif get_resp.status_code == 404:
                sha = None
            elif get_resp.status_code in (401, 403):
                return err(f"GitHub rejected the token ({get_resp.status_code}). Check it has write access to {repo}.")
            else:
                return err(f"GitHub read failed ({get_resp.status_code}): {_gh_message(get_resp)}")

            action = "updated" if sha else "created"
            body: Dict[str, Any] = {
                "message": message or f"{'Update' if sha else 'Add'} detection rule: {name}",
                "content": content_b64,
                "branch": branch,
            }
            if sha:
                body["sha"] = sha

            put_resp = await client.put(f"{GITHUB_API}/repos/{repo}/contents/{target_path}", json=body)
            if put_resp.status_code not in (200, 201):
                return err(f"GitHub publish failed ({put_resp.status_code}): {_gh_message(put_resp)}")
            result = put_resp.json()
    except httpx.HTTPError as exc:
        logger.warning(f"[publish] transport error: {exc}")
        return err(f"Could not reach GitHub: {exc}")

    commit = result.get("commit", {}) or {}
    content = result.get("content", {}) or {}
    logger.info(f"[publish] {action} {repo}/{target_path}@{branch} for customer {customer_code}")
    return {
        "success": True,
        "message": f"Rule {action} in {repo}",
        "action": action,
        "repo": repo,
        "branch": branch,
        "path": target_path,
        "commit_url": commit.get("html_url"),
        "html_url": content.get("html_url"),
        "error": None,
    }
