/**
 * Starter YAML for the detection rule editor.
 *
 * Kept out of the view because it is pure text generation with no reactive state:
 * the view was carrying ~50 lines of literal YAML that had nothing to do with the
 * page's behaviour, and this is the file you actually want to open when the rule
 * schema changes.
 */

export type TemplateKind = "none" | "disabled" | "enabled"

const AGGREGATION_HINT =
	'# Optional — only for threshold / aggregation rules (e.g. "N events per user in 10m").\n' +
	"# Leave enabled: false (or delete this whole block) for a simple match rule.\n"

function baseRule(id: string, today: string): string {
	return `name: New Detection Rule
id: ${id}
version: 1
schema_version: "1.0"
date: "${today}"
author: SOCFortress LLC
description: >
  Describe what this rule detects and why it matters.
data_source:
  - Windows Security Event Log
how_to_implement: >
  What must be collected or enabled for this rule to fire.
known_false_positives: >
  Known benign activity that can trigger this, and how to tune it out.
response:
  risk_score: 50
  severity: medium
tags:
  asset_type: Endpoint
  mitre_attack_id:
    - T1098
  custom_tags:
    - example
  product:
    - Wazuh
  security_domain: endpoint
graylog:
  query: data_win_system_eventID:"4706"
`
}

function aggregationBlock(enabled: boolean): string {
	return `aggregation:
  enabled: ${enabled}
  function: count            # count | distinct_count
  field: null                # required only when function is distinct_count
  group_by:
    - data_win_eventdata_targetUserName
  window: 10m
  threshold: 30
  condition: ">"             # one of  >  >=  <  <=  ==
`
}

/**
 * `none` is a plain match rule, `enabled` a live threshold rule, and `disabled`
 * ships the aggregation block commented as opt-in — that last one is what a fresh
 * editor loads, so the shape is discoverable without being active.
 */
export function makeTemplate(agg: TemplateKind): string {
	const id = globalThis.crypto?.randomUUID?.() ?? "00000000-0000-0000-0000-000000000000"
	const today = new Date().toISOString().slice(0, 10)
	const base = baseRule(id, today)

	if (agg === "none") return base

	const enabled = agg === "enabled"
	return `${base}${enabled ? "" : AGGREGATION_HINT}${aggregationBlock(enabled)}`
}
