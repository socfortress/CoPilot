/**
 * A customer WAF and what it reports (#1165), for `waf-page.spec.ts`.
 *
 * Deterministic: 120 events (more than two pages at 50, so the pagination has a last,
 * short page) and 60 offenders sent in an order that is *not* by threat score, so the
 * list's own ordering is what the rank column shows.
 */

export const WAF_CUSTOMER = "ACME"
export const WAF_ID = 1
export const EVENT_COUNT = 120
export const OFFENDER_COUNT = 60

export const WAF_INSTANCE = {
	id: WAF_ID,
	customer_code: WAF_CUSTOMER,
	name: "edge-waf",
	api_url: "https://waf.acme.test:8080",
	token_prefix: "wafst_AbC12",
	verify_tls: false,
	has_ca_cert: false,
	enabled: true,
	last_verified_at: "2026-10-13T08:00:00Z",
	last_verified_role: "admin",
	created_by: 1,
	created_at: "2026-10-01T08:00:00Z",
	updated_by: 1,
	updated_at: "2026-10-13T08:00:00Z",
	syslog_host: null,
	syslog_port: null,
	graylog_input_id: null,
	graylog_stream_id: null,
	graylog_index_set_id: null,
	forwarding_provisioned_at: null
}

// In the past, so every "last seen" reads as "… ago" whenever the suite runs.
const NOW = Date.parse("2026-10-01T12:00:00Z")
const ACTIONS = ["blocked", "detected", "passed"] as const

/** Event `n` (0 = newest), one minute apart. */
export function wafEvent(n: number) {
	const action = ACTIONS[n % ACTIONS.length]
	return {
		id: `evt-${n}`,
		timestamp: new Date(NOW - n * 60_000).toISOString(),
		transaction_id: `tx-${String(n).padStart(6, "0")}`,
		site_id: "1",
		client_ip: `203.0.113.${n % 250}`,
		method: n % 4 === 0 ? "POST" : "GET",
		uri: `/api/v1/resource/${n}?q=test`,
		host: "app.acme.test",
		rule_id: action === "passed" ? null : "942100",
		action,
		severity: action === "passed" ? null : "CRITICAL",
		anomaly_score: action === "passed" ? 0 : 5 + (n % 5),
		matched_rules:
			action === "passed"
				? []
				: [
						{ id: "942100", msg: "SQL Injection Attack Detected via libinjection" },
						{ id: "949110", msg: "Inbound Anomaly Score Exceeded" }
					],
		geoip_country_code: "NL",
		geoip_country_name: "The Netherlands",
		geoip_city: "Amsterdam"
	}
}

/** Offender `n`: scores go 37, 74, 11, 48, … so the WAF's order is not the ranking. */
export function wafOffender(n: number) {
	const score = (n * 37) % 100
	return {
		ip_address: `198.51.100.${n}`,
		block_count: score * 10,
		rule_hit_count: score * 3,
		total_events: score * 12 + 5,
		threat_score: score,
		top_rules: [
			{ rule_id: "942100", count: score },
			{ rule_id: "920350", count: 3 },
			{ rule_id: "913100", count: 1 }
		],
		country_code: n % 2 ? "BG" : "NL",
		country_name: n % 2 ? "Bulgaria" : "The Netherlands",
		first_seen_at: "2026-10-01T08:00:00Z",
		last_seen_at: new Date(NOW - n * 3_600_000).toISOString(),
		is_blocked: n % 7 === 0
	}
}

export const OFFENDERS = Array.from({ length: OFFENDER_COUNT }, (_, n) => wafOffender(n))
export const TOP_OFFENDER = [...OFFENDERS].sort((a, b) => b.threat_score - a.threat_score)[0]

export const WAF_STATS = {
	total_1h: 4821,
	blocked_1h: 312,
	detected_1h: 57,
	block_rate: 0.0647,
	top_rules: [
		{ rule_id: "942100", count: 120 },
		{ rule_id: "920350", count: 44 }
	],
	top_ips: [
		{ client_ip: "203.0.113.7", count: 98 },
		{ client_ip: "203.0.113.9", count: 41 }
	],
	requests_per_hour: Array.from({ length: 24 }, (_, h) => ({
		hour: new Date(NOW - (23 - h) * 3_600_000).toISOString(),
		count: 1500 + Math.round(900 * Math.sin(h / 3))
	})),
	attack_categories: [
		{ category: "SQL injection", count: 210 },
		{ category: "Protocol violation", count: 90 }
	],
	top_countries: [
		{ country_code: "NL", country_name: "The Netherlands", count: 2100 },
		{ country_code: "BG", country_name: "Bulgaria", count: 870 }
	],
	ingestion_lag_seconds: 2.4,
	events_per_minute: 81.3,
	caddy_healthy: true
}
