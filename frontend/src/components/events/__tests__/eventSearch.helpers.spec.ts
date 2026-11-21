import type { EventSource } from "@/types/event-sources"
import { describe, expect, it } from "vitest"
import {
	conflictingFieldsInQuery,
	fieldsInQuery,
	indexMatchesPattern,
	resolveSourceForIndex,
	routeSourceNames,
	timeFieldMismatch
} from "../eventSearch.helpers"

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

	it("reads a comma list as the indexer does: any part can claim the index", () => {
		expect(indexMatchesPattern("mikrotik-acme-0", "fortigate-acme*,mikrotik-acme*")).toBe(true)
		expect(indexMatchesPattern("cisco-acme-0", "fortigate-acme*, mikrotik-acme*")).toBe(false)
	})

	it("lets an exclusion remove only what the parts before it matched", () => {
		expect(indexMatchesPattern("mikrotik-acme-old-0", "mikrotik-acme*,-mikrotik-acme-old*")).toBe(false)
		expect(indexMatchesPattern("mikrotik-acme-0", "mikrotik-acme*,-mikrotik-acme-old*")).toBe(true)
		// Nothing before it to remove from, so it removes nothing; and a later part adds back.
		expect(indexMatchesPattern("mikrotik-acme-old-0", "-mikrotik-acme-old*,mikrotik-acme*")).toBe(true)
		expect(
			indexMatchesPattern("mikrotik-acme-old-0", "mikrotik-acme*,-mikrotik-acme-old*,mikrotik-acme-old-0")
		).toBe(true)
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

	it("judges a comma pattern by the part that claims the index", () => {
		const combined = source({ name: "Network", index_pattern: "*,fortigate-acme-*" })
		const broad = source({ name: "All Fortigate", index_pattern: "fortigate-*" })

		expect(resolveSourceForIndex("fortigate-acme-2026.09.08", [broad, combined])?.name).toBe("Network")
		expect(resolveSourceForIndex("cisco-acme-2026.09.08", [broad, combined])?.name).toBe("Network")
	})

	it("ignores a source whose exclusion removes the index", () => {
		const current = source({ name: "Current", index_pattern: "office365-acme-*,-office365-acme-2025*" })

		expect(resolveSourceForIndex("office365-acme-2025.12.31", [current])).toBeNull()
		expect(resolveSourceForIndex("office365-acme-2026.01.01", [current])?.name).toBe("Current")
	})

	it("takes the first of two equally specific patterns, as the backend does", () => {
		const first = source({ name: "First", index_pattern: "logs-*" })
		const second = source({ name: "Second", index_pattern: "logs-*" })

		expect(resolveSourceForIndex("logs-1", [first, second])?.name).toBe("First")
	})
})

describe("timeFieldMismatch", () => {
	it("is null while every source names the same time field", () => {
		expect(timeFieldMismatch([])).toBeNull()
		expect(
			timeFieldMismatch([
				{ name: "Firewall", time_field: "timestamp" },
				{ name: "Router", time_field: "timestamp" }
			])
		).toBeNull()
	})

	it("names each source's field when they differ", () => {
		expect(
			timeFieldMismatch([
				{ name: "Firewall", time_field: "timestamp" },
				{ name: "Cloud", time_field: "@timestamp" }
			])
		).toBe("Firewall: timestamp, Cloud: @timestamp")
	})
})

describe("fieldsInQuery", () => {
	it("finds every field a query names, once, in order", () => {
		expect(fieldsInQuery("src_ip:10.0.0.5 AND (dst_ip:10.0.0.6 OR src_ip:10.0.0.7)")).toEqual(["src_ip", "dst_ip"])
		expect(fieldsInQuery("agent.labels.customer:acme")).toEqual(["agent.labels.customer"])
		expect(fieldsInQuery("@timestamp:[now-1h TO now]")).toEqual(["@timestamp"])
	})

	it("reads fields after operators", () => {
		expect(fieldsInQuery("NOT action:allow -rule_level:3 +user:jdoe !host:web")).toEqual([
			"action",
			"rule_level",
			"user",
			"host"
		])
	})

	it("never reads a value as a field", () => {
		expect(fieldsInQuery('message:"user: admin logged in"')).toEqual(["message"])
		expect(fieldsInQuery('message:"quoted \\" user: x"')).toEqual(["message"])
		expect(fieldsInQuery("src_ip:fe80::1 AND url:https://example.com")).toEqual(["src_ip", "url"])
		expect(fieldsInQuery("timestamp:[2026-01-01T10:00:00 TO 2026-01-02T10:00:00]")).toEqual(["timestamp"])
		expect(fieldsInQuery("just some words")).toEqual([])
	})
})

describe("conflictingFieldsInQuery", () => {
	const mappings = [
		{ field: "src_ip", type: "ip, keyword", conflict: true },
		{ field: "action", type: "keyword", conflict: false },
		{ field: "rule_level", type: "keyword, long", conflict: true },
		{ field: "user", type: "keyword" }
	]

	it("lists the fields the query names that are typed differently, in query order", () => {
		expect(conflictingFieldsInQuery("rule_level:>5 AND src_ip:10.0.0.0/8 AND action:deny", mappings)).toEqual([
			mappings[2],
			mappings[0]
		])
	})

	it("is empty when the query names none of them", () => {
		expect(conflictingFieldsInQuery("action:deny AND user:jdoe", mappings)).toEqual([])
		expect(conflictingFieldsInQuery('message:"src_ip:10.0.0.5"', mappings)).toEqual([])
		expect(conflictingFieldsInQuery("", mappings)).toEqual([])
	})
})

describe("routeSourceNames", () => {
	it("reads one name or several", () => {
		expect(routeSourceNames("Firewall")).toEqual(["Firewall"])
		expect(routeSourceNames(["Firewall", "Router"])).toEqual(["Firewall", "Router"])
	})

	it("drops blanks, nulls and repeats", () => {
		expect(routeSourceNames(["Firewall", null, " ", "Firewall", " Router "])).toEqual(["Firewall", "Router"])
		expect(routeSourceNames(undefined)).toEqual([])
		expect(routeSourceNames(null)).toEqual([])
	})
})
