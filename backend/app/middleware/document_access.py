"""Which indexer documents a caller may read.

The indexer has no tenants: every customer's index is one search away from any route that takes an
index name or pattern, and from every route that searches all indices. Since #1219 an analyst or a
responder sees only the customers assigned to them, so these routes apply the caller's customers to
what comes back, deciding a document's customer the way ingest does
(``incident_alert.resolve_customer_code``):

- ``scoped_codes``: ``None`` for a deployment-wide caller (an admin), else the caller's codes.
- ``ensure_document_access``: one document, once fetched and before anything of it is returned,
  sent elsewhere or acted on. Its customer must be the caller's; a document that names no customer
  is refused. Both are the same 404 as a missing document, so ids can't be probed.
- ``customer_filter``: a clause to AND into a search or an aggregation, so only the caller's
  customers' documents match, whatever index the caller named (``None`` for an admin).
- ``index_visible`` / ``visible_index_names``: for the routes that show only index names or
  mappings, judged by the index name (``customer_index.index_matches_customer``).

The filter mirrors ingest's order: a document carrying an agent customer label belongs to that
label's customer and nothing else on it counts; only without one do the syslog customer, the
customer code, the Office 365 tenant, the AWS account and the Wazuh worker node decide. A field some
index maps as text is matched through its ``.keyword`` subfield only, since ``terms`` on an analysed
field would let a code match a token of another customer's value (``acme`` in ``acme-2``).
"""

import time
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import Set

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.middleware.customer_access import customer_access_handler

DOCUMENT_NOT_FOUND = "Document not found"
INDEX_NOT_FOUND = "Index not found"

LABEL_FIELDS = ("agent_labels_customer", "agent.labels.customer")
CODE_FIELDS = ("syslog_customer", "customer_code")
OFFICE365_FIELD = "data_office365_OrganizationId"
AWS_FIELD = "aws_account_id"
CLUSTER_NODE_FIELD = "cluster_node"
WORKER_PREFIX = "wazuh.worker."
CUSTOMER_FIELDS = (*LABEL_FIELDS, *CODE_FIELDS, OFFICE365_FIELD, AWS_FIELD, CLUSTER_NODE_FIELD)

#: Matches nothing: the filter of a caller who sees no customer.
MATCH_NONE = {"bool": {"must_not": [{"match_all": {}}]}}

#: How long the field types of an index pattern are kept (mappings change only with new templates).
FIELD_TYPES_TTL_SECONDS = 300
FIELD_TYPES_CACHE_SIZE = 64
_field_types_cache: Dict[str, tuple] = {}


async def scoped_codes(user: User, session: AsyncSession) -> Optional[List[str]]:
    """``None`` for a deployment-wide caller, else the customer codes the caller may see (possibly none)."""
    accessible = await customer_access_handler.get_user_accessible_customers(user, session)
    if "*" in accessible:
        return None
    return sorted(set(accessible))


def _folded(codes: Iterable[str]) -> Set[str]:
    # Customer codes compare with the column's collation, case-insensitively, so ``ACME`` and
    # ``acme`` are one customer: a label written in another case still names it.
    return {code.casefold() for code in codes}


async def document_customer(source: dict, session: AsyncSession) -> Optional[str]:
    """The customer a document belongs to, by ingest's rule, or ``None`` when nothing on it names one.

    Ingest reads flat fields (what Graylog writes); a document straight from Wazuh carries the
    agent's label nested, so ``agent.labels.customer`` is read when no flat field decides.
    """
    from app.incidents.services.incident_alert import resolve_customer_code

    customer = await resolve_customer_code(source or {}, session)
    if customer:
        return customer
    agent = (source or {}).get("agent")
    labels = agent.get("labels") if isinstance(agent, dict) else None
    nested = labels.get("customer") if isinstance(labels, dict) else None
    return str(nested) if nested else None


async def document_visible(user: User, source: Optional[dict], session: AsyncSession) -> bool:
    """Whether ``user`` may see the customer the document ``source`` belongs to (always, for an admin)."""
    codes = await scoped_codes(user, session)
    if codes is None:
        return True
    customer = await document_customer(source or {}, session)
    return customer is not None and customer.casefold() in _folded(codes)


async def ensure_document_access(user: User, source: Optional[dict], session: AsyncSession) -> None:
    """404 unless ``user`` may see the customer the document ``source`` belongs to."""
    if not await document_visible(user, source, session):
        raise HTTPException(status_code=404, detail=DOCUMENT_NOT_FOUND)


async def customer_filter(user: User, session: AsyncSession, index: str = "*") -> Optional[dict]:
    """``None`` for a deployment-wide caller, else a clause matching only their customers' documents in ``index``."""
    codes = await scoped_codes(user, session)
    if codes is None:
        return None
    return await customer_filter_for(codes, session, index)


async def customer_filter_for(codes: List[str], session: AsyncSession, index: str = "*") -> dict:
    """A clause matching the documents of ``codes`` (``MATCH_NONE`` for no codes)."""
    if not codes:
        return MATCH_NONE
    values = sorted({variant for code in codes for variant in (code, code.lower(), code.upper())})
    text_fields = await _text_typed_fields(index)

    def exact(field: str, wanted: List[str]) -> List[dict]:
        # ``.keyword`` matches exactly wherever the field is a text multi-field; the field itself only
        # where no index maps it as text.
        clauses = [{"terms": {f"{field}.keyword": wanted}}]
        if field not in text_fields:
            clauses.append({"terms": {field: wanted}})
        return clauses

    labelled = [clause for field in LABEL_FIELDS for clause in exact(field, values)]
    others = [clause for field in CODE_FIELDS for clause in exact(field, values)]
    tenants = await office365_tenants(codes, session)
    if tenants:
        others.extend(exact(OFFICE365_FIELD, tenants))
    accounts = await aws_accounts(codes, session)
    if accounts:
        others.extend(exact(AWS_FIELD, accounts))
    node_field = f"{CLUSTER_NODE_FIELD}.keyword" if CLUSTER_NODE_FIELD in text_fields else CLUSTER_NODE_FIELD
    for value in values:
        others.append({"term": {node_field: f"{WORKER_PREFIX}{value}"}})
        others.append({"prefix": {node_field: f"{WORKER_PREFIX}{value}."}})

    no_label = [{"exists": {"field": field}} for field in LABEL_FIELDS]
    return {
        "bool": {
            "should": [*labelled, {"bool": {"should": others, "minimum_should_match": 1, "must_not": no_label}}],
            "minimum_should_match": 1,
        },
    }


async def _text_typed_fields(index: str) -> Set[str]:
    """The customer fields some index under ``index`` maps as text. Unknown (no answer) counts as all of them."""
    cached = _field_types_cache.get(index)
    if cached and time.monotonic() - cached[0] < FIELD_TYPES_TTL_SECONDS:
        return cached[1]
    from app.connectors.wazuh_indexer.utils.universal import (
        create_wazuh_indexer_client_async,
    )

    try:
        es_client = await create_wazuh_indexer_client_async("Wazuh-Indexer")
        try:
            response = await es_client.field_caps(
                index=index,
                fields=",".join(CUSTOMER_FIELDS),
                ignore_unavailable=True,
                allow_no_indices=True,
            )
        finally:
            await es_client.close()
    except Exception as e:
        # Fail closed: matched through ``.keyword`` only, a scoped caller sees less, never more.
        logger.warning(f"Could not read the customer fields' types for {index}: {e}")
        return set(CUSTOMER_FIELDS)
    text = {name for name, types in (response.get("fields") or {}).items() if isinstance(types, dict) and "text" in types}
    if len(_field_types_cache) >= FIELD_TYPES_CACHE_SIZE:
        # The pattern can come from a request: keep the cache bounded, oldest out first.
        _field_types_cache.pop(min(_field_types_cache, key=lambda key: _field_types_cache[key][0]))
    _field_types_cache[index] = (time.monotonic(), text)
    return text


async def office365_tenants(codes: List[str], session: AsyncSession) -> List[str]:
    """The Microsoft 365 tenant ids configured for ``codes`` (what ingest resolves a tenant to a customer by)."""
    from app.integrations.models.customer_integration_settings import (
        CustomerIntegrations,
    )
    from app.integrations.models.customer_integration_settings import (
        IntegrationAuthKeys,
    )
    from app.integrations.models.customer_integration_settings import IntegrationService
    from app.integrations.models.customer_integration_settings import (
        IntegrationSubscription,
    )

    result = await session.execute(
        select(IntegrationAuthKeys.auth_value)
        .join(IntegrationSubscription, IntegrationAuthKeys.subscription_id == IntegrationSubscription.id)
        .join(IntegrationService, IntegrationSubscription.integration_service_id == IntegrationService.id)
        .join(CustomerIntegrations, CustomerIntegrations.id == IntegrationSubscription.customer_id)
        .where(
            IntegrationService.service_name == "Office365",
            IntegrationAuthKeys.auth_key_name == "TENANT_ID",
            CustomerIntegrations.customer_code.in_(codes),
        ),
    )
    return sorted({value for value in result.scalars().all() if value})


async def aws_accounts(codes: List[str], session: AsyncSession) -> List[str]:
    """The AWS accounts that ingest would resolve to one of ``codes``: deployed instances, claimed by no other customer."""
    from app.integrations.aws.services.account_lookup import AWS_INTEGRATION_NAME
    from app.integrations.models.customer_integration_settings import (
        CustomerIntegrations,
    )
    from app.integrations.models.customer_integration_settings import (
        IntegrationAuthKeys,
    )
    from app.integrations.models.customer_integration_settings import IntegrationService
    from app.integrations.models.customer_integration_settings import (
        IntegrationSubscription,
    )

    result = await session.execute(
        select(IntegrationAuthKeys.auth_value, CustomerIntegrations.customer_code)
        .join(IntegrationSubscription, IntegrationAuthKeys.subscription_id == IntegrationSubscription.id)
        .join(IntegrationService, IntegrationSubscription.integration_service_id == IntegrationService.id)
        .join(CustomerIntegrations, CustomerIntegrations.id == IntegrationSubscription.customer_id)
        .where(
            IntegrationService.service_name == AWS_INTEGRATION_NAME,
            IntegrationAuthKeys.auth_key_name == "AWS_ACCOUNT_ID",
            CustomerIntegrations.deployed.is_(True),
        ),
    )
    owners: Dict[str, Set[str]] = {}
    for account, code in result.all():
        if account:
            owners.setdefault(account, set()).add(code.casefold())
    wanted = _folded(codes)
    # An account two customers claim routes to nobody at ingest, so it counts for nobody here.
    return sorted(account for account, claimants in owners.items() if len(claimants) == 1 and claimants <= wanted)


async def index_visible(user: User, index_name: str, session: AsyncSession) -> bool:
    """Whether ``user`` may see an index by its name: every index for an admin, their customers' for anyone else."""
    codes = await scoped_codes(user, session)
    if codes is None:
        return True
    return bool(await visible_index_names(codes, [index_name], session))


async def ensure_index_visible(user: User, index_name: str, session: AsyncSession) -> None:
    """404 unless ``user`` may see the index ``index_name``."""
    if not await index_visible(user, index_name, session):
        raise HTTPException(status_code=404, detail=INDEX_NOT_FOUND)


async def visible_index_names(codes: List[str], names: Iterable[str], session: AsyncSession) -> List[str]:
    """The names among ``names`` that belong to one of ``codes`` (none for no codes)."""
    from app.connectors.wazuh_indexer.utils.customer_index import (
        build_customer_index_matchers,
    )
    from app.connectors.wazuh_indexer.utils.customer_index import index_matches_customer

    names = list(names)
    if not codes or not names:
        return []
    matchers = await build_customer_index_matchers(session, codes)
    return [name for name in names if index_matches_customer(name, matchers)]


async def agent_filters(user: User, session: AsyncSession) -> Optional[List[dict]]:
    """For Wazuh's state indices, which name an agent but no customer: ``None`` for an admin, else
    filters keeping the documents of the caller's customers' agents, by id, name and the exact pair
    (the Exposure page's rule, ``exposure_vulnerabilities.scope_filter``: an agent id is unique per
    manager only, so neither the id nor the name alone is an agent)."""
    codes = await scoped_codes(user, session)
    if codes is None:
        return None
    from app.customer_portal.services.exposure_vulnerabilities import PAIR_SCRIPT
    from app.customer_portal.services.exposure_vulnerabilities import pair_key
    from app.db.universal_models import Agents

    if not codes:
        return [MATCH_NONE]
    rows = await session.execute(select(Agents.agent_id, Agents.hostname).where(Agents.customer_code.in_(codes)))
    agents = sorted({(str(agent_id), hostname) for agent_id, hostname in rows.all() if agent_id and hostname})
    if not agents:
        return [MATCH_NONE]
    return [
        {"terms": {"agent.id": sorted({agent_id for agent_id, _ in agents})}},
        {"terms": {"agent.name": sorted({hostname for _, hostname in agents})}},
        {
            "script": {
                "script": {
                    "source": PAIR_SCRIPT,
                    "lang": "painless",
                    "params": {"pairs": {pair_key(agent_id, hostname): 1 for agent_id, hostname in agents}},
                },
            },
        },
    ]
