import type { EventSearchMemory, EventSearchResult, EventSourceItem, FieldMapping } from "../../src/types/siem"

/**
 * What the indexer would answer for event search (#1258). The e2e backend runs without a
 * Wazuh indexer, so `event-search.cy.ts` serves these at the network layer; the tenancy of
 * the same routes is the backend's own test (tests/e2e/event_search_e2e.py). The user's
 * saved and recent searches and columns are not faked: they go to the real backend.
 */

export const EVENT_TOTAL = 70
export const PAGE = 50

export function eventSources(customerCode: string): EventSourceItem[] {
	const base = { customer_code: customerCode, enabled: true, created_at: "2026-09-01T00:00:00", updated_at: "2026-09-01T00:00:00" }
	return [
		{ ...base, id: 1, name: "Wazuh Alerts", index_pattern: "wazuh-*", event_type: "EDR", time_field: "timestamp", displayed_columns: null },
		{
			...base,
			id: 2,
			name: "Office 365",
			index_pattern: "office365-*",
			event_type: "SaaS",
			time_field: "timestamp",
			displayed_columns: [
				{ key: "timestamp", label: "Time" },
				{ key: "data_office365_UserId", label: "User" }
			]
		}
	]
}

export const FIELDS: FieldMapping[] = [
	{ field: "timestamp", type: "date" },
	{ field: "agent_name", type: "keyword" },
	{ field: "rule_level", type: "long" },
	{ field: "rule_description", type: "text" },
	{ field: "data_srcip", type: "ip" },
	{ field: "data_office365_UserId", type: "keyword" }
]

/** Event `n` (0 = newest): one minute apart, offset-less UTC times like several sources write. */
export function event(n: number): EventSearchResult {
	return {
		_id: `evt-${n}`,
		_index: "wazuh-alerts-4.x-2026.10.01",
		timestamp: new Date(Date.UTC(2026, 9, 1, 12, 0, 0) - n * 60_000).toISOString().replace("Z", ""),
		agent_name: `web-${String(n % 5).padStart(2, "0")}`,
		rule_level: 3 + (n % 10),
		rule_description: n % 2 ? "sshd: authentication failed" : "Login session opened",
		data_srcip: `203.0.113.${n}`,
		data_office365_UserId: `user${n}@acme.test`
	} as unknown as EventSearchResult
}

/**
 * Empties the portal user's event search memory for `customerCode`, through the API: it
 * lives on the server, so a test that expects a clean slate must ask for one.
 */
export function resetEventSearchMemory(seed: { portal_user: string; password: string }, customerCode: string) {
	return cy
		.request({
			method: "POST",
			url: "/api/auth/token/customer-portal",
			form: true,
			body: { username: seed.portal_user, password: seed.password }
		})
		.then(login => {
			const headers = { Authorization: `Bearer ${login.body.access_token as string}` }
			const base = `/api/siem/event_search/${customerCode}`
			cy.request({ url: base, headers }).then(response => {
				const memory = response.body as EventSearchMemory
				for (const saved of memory.saved) cy.request({ method: "DELETE", url: `${base}/saved/${saved.id}`, headers })
				for (const source of Object.keys(memory.columns)) {
					cy.request({ method: "PUT", url: `${base}/columns`, headers, body: { source_name: source, columns: null } })
				}
				cy.request({ method: "DELETE", url: `${base}/recent`, headers })
			})
		})
}
