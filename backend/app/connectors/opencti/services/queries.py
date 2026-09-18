"""
GraphQL documents CoPilot sends to OpenCTI.

Kept apart from the service functions so a new feature can reuse the shared
fragments below instead of re-listing the same fields. Every document takes
user input as `$variables`; nothing is ever interpolated into the text.

A GraphQL document must define exactly the fragments it spreads — an unused
one fails validation (`NoUnusedFragments`) — so each query appends only the
fragments it uses.
"""

# Fields every STIX core object carries, flattened into `OpenCTIObjectMeta`.
CORE_META_FRAGMENT = """
fragment CoreMeta on StixCoreObject {
    id
    standard_id
    entity_type
    created_at
    updated_at
    createdBy { name }
    objectLabel { value color }
    objectMarking { definition }
}
"""

# Spreads CoreMeta, so a document using it needs CORE_META_FRAGMENT too.
INDICATOR_FRAGMENT = """
fragment IndicatorFields on Indicator {
    ...CoreMeta
    name
    description
    pattern
    pattern_type
    x_opencti_main_observable_type
    x_opencti_score
    confidence
    valid_from
    valid_until
    revoked
}
"""

ABOUT_QUERY = """
query CoPilotAbout {
    about {
        version
        dependencies { name version }
    }
    me { name user_email }
}
"""

# `value` covers every observable with a single value (IPs, domains, hostnames,
# URLs, emails, …). Files carry no `value` — they are matched on their hashes —
# so the lookup ORs all of these keys in one filter item.
OBSERVABLE_LOOKUP_KEYS = ["value", "hashes.MD5", "hashes.SHA-1", "hashes.SHA-256", "hashes.SHA-512"]

OBSERVABLE_LOOKUP_QUERY = (
    """
query CoPilotObservableLookup($filters: FilterGroup, $first: Int, $indicators: Int, $reports: Int) {
    stixCyberObservables(first: $first, filters: $filters) {
        pageInfo { globalCount }
        edges {
            node {
                ...CoreMeta
                observable_value
                x_opencti_description
                x_opencti_score
                ... on StixFile { name hashes { algorithm hash } }
                indicators(first: $indicators) {
                    pageInfo { globalCount }
                    edges { node { ...IndicatorFields } }
                }
                reports(first: $reports) {
                    pageInfo { globalCount }
                    edges { node { id name published } }
                }
            }
        }
    }
}
"""
    + CORE_META_FRAGMENT
    + INDICATOR_FRAGMENT
)

INDICATORS_QUERY = (
    """
query CoPilotIndicators($search: String, $filters: FilterGroup, $first: Int, $after: ID) {
    indicators(search: $search, filters: $filters, first: $first, after: $after, orderBy: created_at, orderMode: desc) {
        pageInfo { globalCount hasNextPage endCursor }
        edges { node { ...IndicatorFields } }
    }
}
"""
    + CORE_META_FRAGMENT
    + INDICATOR_FRAGMENT
)

ENTITY_QUERY = (
    """
query CoPilotEntity($id: String!) {
    stixCoreObject(id: $id) {
        ...CoreMeta
        parent_types
        representative { main secondary }
        externalReferences(first: 25) {
            edges { node { source_name url external_id description } }
        }
        ... on StixDomainObject { confidence }
        ... on StixCyberObservable { x_opencti_score }
        ... on Indicator { x_opencti_score }
    }
}
"""
    + CORE_META_FRAGMENT
)
