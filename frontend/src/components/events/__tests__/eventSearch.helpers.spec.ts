import type { EventSource } from "@/types/event-sources"
import { describe, expect, it } from "vitest"
import { indexMatchesPattern, resolveSourceForIndex } from "../eventSearch.helpers"

function source(partial: Partial<EventSource> & Pick<EventSource, "name" | "index_pattern">): EventSource {
	return {
		id: 1,
		customer_code: "ACME",
		event_type: "EDR",
		time_field: "timestamp",
		enabled: true,
		created_at: "2026-01-01T00:00:00Z",
		updated_at: "2026-01-01T00:00:00Z",
		...partial
	}
}

describe("indexMatchesPattern", () => {
	it("matches a trailing wildcard against a dated index", () => {
		expect(indexMatchesPattern("wazuh-alerts-4.x-2026.09.08", "wazuh-alerts-*")).toBe(true)
		expect(indexMatchesPattern("office365-acme-2026.09.08", "office365-acme-*")).toBe(true)
	})

	it("treats a dot as a literal", () => {
		// The whole reason the pattern is escaped: `.` as a regex wildcard would let a
		// hyphenated pattern claim an underscored index, and every index name is dots.
		expect(indexMatchesPattern("wazuh_alerts_x", "wazuh.alerts.*")).toBe(false)
		expect(indexMatchesPattern("wazuh.alerts.x", "wazuh.alerts.*")).toBe(true)
	})

	it("anchors both ends", () => {
		expect(indexMatchesPattern("not-wazuh-alerts-2026", "wazuh-alerts-*")).toBe(false)
		expect(indexMatchesPattern("wazuh-alerts", "wazuh-alerts-*")).toBe(false)
	})

	it("supports `?` as exactly one character", () => {
		expect(indexMatchesPattern("logs-1", "logs-?")).toBe(true)
		expect(indexMatchesPattern("logs-42", "logs-?")).toBe(false)
	})

	it("matches everything under a bare `*`", () => {
		expect(indexMatchesPattern("anything-at-all", "*")).toBe(true)
	})

	it("is false for an empty index or pattern rather than throwing", () => {
		expect(indexMatchesPattern("", "wazuh-*")).toBe(false)
		expect(indexMatchesPattern("wazuh-alerts-2026", "")).toBe(false)
	})
})

describe("resolveSourceForIndex", () => {
	const wazuh = source({ name: "Wazuh EDR", index_pattern: "wazuh-alerts-*" })
	const office = source({
		name: "Office 365 Audit",
		index_pattern: "office365-acme-*",
		event_type: "Cloud Integration"
	})

	it("resolves an index to the source whose pattern claims it", () => {
		expect(resolveSourceForIndex("office365-acme-2026.09.08", [wazuh, office])?.name).toBe("Office 365 Audit")
		expect(resolveSourceForIndex("wazuh-alerts-2026.09.08", [wazuh, office])?.name).toBe("Wazuh EDR")
	})

	it("returns null when no pattern claims the index", () => {
		expect(resolveSourceForIndex("crowdstrike-acme-2026.09.08", [wazuh, office])).toBeNull()
		expect(resolveSourceForIndex("wazuh-alerts-2026.09.08", [])).toBeNull()
	})

	it("skips disabled sources — they are not selectable in the filter bar", () => {
		const disabled = source({ name: "Office 365 Audit", index_pattern: "office365-acme-*", enabled: false })
		expect(resolveSourceForIndex("office365-acme-2026.09.08", [disabled])).toBeNull()
	})

	it("prefers the most specific pattern when several match", () => {
		const catchAll = source({ name: "Everything", index_pattern: "*" })
		const broad = source({ name: "All Office", index_pattern: "office365-*" })

		expect(resolveSourceForIndex("office365-acme-2026.09.08", [catchAll, broad, office])?.name).toBe(
			"Office 365 Audit"
		)
		// Order of the list must not decide it.
		expect(resolveSourceForIndex("office365-acme-2026.09.08", [office, broad, catchAll])?.name).toBe(
			"Office 365 Audit"
		)
	})
})
