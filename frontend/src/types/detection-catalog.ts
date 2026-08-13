// Mirrors backend/app/integrations/copilot_searches/schema/copilot_searches.py
// Detection Catalog block. Field shapes track FastAPI's response models
// verbatim (snake_case kept on the wire).

export interface CatalogStoryRow {
	name: string
	data_sources: string[]
	tactics: string[]
	products: string[]
	date: string | null
	detection_count: number
}

export interface CatalogStoryListResponse {
	stories: CatalogStoryRow[]
}

export interface CatalogStoryDetection {
	id: string
	name: string
	type: string
	severity: string | null
	mitre_attack_id: string[]
	tactics: string[]
	description: string | null
}

export interface CatalogStoryDetailResponse {
	name: string
	id: string
	description: string
	why_it_matters: string
	detections: CatalogStoryDetection[]
	data_sources: string[]
	tactics: string[]
	products: string[]
	authors: string[]
	references: string[]
	date: string | null
	version: number | null
	detection_count: number
}

export interface CatalogStatsResponse {
	detection_count: number
	story_count: number
	product_count: number
	data_source_count: number
	tactic_count: number
	last_refresh: string | null
	// Wazuh-side counts — present on every response; default to 0 / true /
	// null when the deployment has never loaded the Wazuh cache.
	wazuh_rule_count: number
	wazuh_last_refresh: string | null
	wazuh_available: boolean
	wazuh_unavailable_reason: string | null
}

// ---------------------------------------------------------------------------
// Wazuh Rules tab
// ---------------------------------------------------------------------------

export interface CatalogWazuhRuleRow {
	id: number | null
	level: number | null
	status: string | null
	description: string
	filename: string
	relative_dirname: string
	groups: string[]
	mitre: string[]
	hits_7d: number
	hits_30d: number
	// ISO timestamp of the rule's most recent firing in the 30d window,
	// or null when the rule hasn't fired / firing stats are unavailable.
	last_seen: string | null
}

export interface CatalogWazuhRulesResponse {
	rules: CatalogWazuhRuleRow[]
	total: number
	available: boolean
	unavailable_reason: string | null
	last_refresh: string | null
	// Indexer-side availability for the firing-stats column. Distinct from
	// `available` (Wazuh Manager status) because the two backends can fail
	// independently.
	firing_stats_available: boolean
	firing_stats_unavailable_reason: string | null
	firing_stats_last_refresh: string | null
	// Echoes the customer scope: "" for global, customer code when scoped.
	customer_code: string
}

export interface CatalogWazuhRuleCompliance {
	pci_dss: string[]
	gdpr: string[]
	hipaa: string[]
	nist_800_53: string[]
	tsc: string[]
	gpg13: string[]
}

export interface CatalogWazuhRuleDetailResponse {
	id: number | null
	level: number | null
	status: string | null
	description: string
	filename: string
	relative_dirname: string
	groups: string[]
	mitre: string[]
	tactics: string[]
	compliance: CatalogWazuhRuleCompliance
	// Free-form: keys vary per rule (if_sid, match, regex, decoded_as, …).
	// The modal iterates whatever arrives.
	details: Record<string, unknown>
	// Reconstructed <rule>...</rule> XML synthesized server-side from the
	// cached fields. Displayed as a code snippet in the modal's "Rule Source"
	// section. Empty string when the cache doesn't have enough to render.
	source_xml: string
	// Firing counts (mirrored on the row-level type above). Same "0 means
	// 0 only when firing_stats_available is true" semantics.
	hits_7d: number
	hits_30d: number
	last_seen: string | null
	firing_stats_available: boolean
	firing_stats_unavailable_reason: string | null
}

// ---------------------------------------------------------------------------
// Coverage Gaps tab
// ---------------------------------------------------------------------------

export interface CatalogCoverageGapRow {
	technique_id: string
	technique_name: string
	tactics: string[]
	url: string | null
}

export interface CatalogCoverageGapsResponse {
	gaps: CatalogCoverageGapRow[]
	gap_count: number
	covered_count: number
	total_techniques: number
	coverage_pct: number
}

// ---------------------------------------------------------------------------
// Logtest — paste a raw log line, see which rule matches
// ---------------------------------------------------------------------------

export interface CatalogLogTestRequest {
	event: string
	log_format?: string
	location?: string
}

export interface CatalogLogTestRuleSummary {
	id: number | null
	level: number | null
	description: string
	groups: string[]
	mitre: string[]
	pci_dss: string[]
	gdpr: string[]
	hipaa: string[]
	nist_800_53: string[]
	firedtimes: number | null
}

export interface CatalogLogTestResponse {
	matched: boolean
	rule: CatalogLogTestRuleSummary | null
	tactics: string[]
	alert: Record<string, unknown> | null
	unavailable_reason: string | null
}

// ---------------------------------------------------------------------------
// Compliance pivot tab
// ---------------------------------------------------------------------------

export interface CatalogComplianceFramework {
	key: string // API value: pci_dss, hipaa, etc.
	label: string // UI: "PCI DSS", "HIPAA"
}

export interface CatalogComplianceFrameworksResponse {
	frameworks: CatalogComplianceFramework[]
}

export interface CatalogComplianceGroupRow {
	control: string
	rule_count: number
	rule_ids: number[]
	total_hits_30d: number
	total_hits_7d: number
}

export interface CatalogComplianceResponse {
	framework: string
	framework_label: string
	groups: CatalogComplianceGroupRow[]
	control_count: number
	rules_with_compliance: number
	total_rules: number
	firing_stats_available: boolean
}

export interface CatalogComplianceGroupDetailResponse {
	framework: string
	framework_label: string
	group: CatalogComplianceGroupRow
	firing_stats_available: boolean
}
