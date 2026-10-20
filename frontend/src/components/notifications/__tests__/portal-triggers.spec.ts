import { describe, expect, it } from "vitest"
import {
	INTERNAL_TRIGGERS,
	isInternalTrigger,
	isPortalTrigger,
	NOTIFICATION_TRIGGER_LABELS,
	PORTAL_TRIGGERS
} from "@/types/notifications"
import { PORTAL_SNIPPETS, snippetsForTrigger, variablesForTrigger } from "../templateVariables"

/** The Customer Portal's emails to its users (#1282): template scopes, never routes. */
describe("portal email triggers", () => {
	it("are labelled as portal emails, and are not route triggers of either scope", () => {
		expect(PORTAL_TRIGGERS).toHaveLength(5)
		for (const trigger of PORTAL_TRIGGERS) {
			expect(NOTIFICATION_TRIGGER_LABELS[trigger]).toMatch(/^Portal email — /)
			expect(isPortalTrigger(trigger)).toBe(true)
			expect(INTERNAL_TRIGGERS).not.toContain(trigger)
			expect(isInternalTrigger(trigger)).toBe(false)
		}
		expect(isPortalTrigger("alert_created")).toBe(false)
		expect(isPortalTrigger(null)).toBe(false)
	})

	it("advertise the portal's own variables, and nothing an alert route carries", () => {
		const names = variablesForTrigger("portal_digest").map(v => v.name)
		expect(names).toEqual(
			expect.arrayContaining(["user_name", "customer_name", "portal_url", "items", "item_count", "link_url"])
		)
		for (const absent of ["context.iocs", "assignee", "temp_password", "context.ai_report", "report_url"]) {
			expect(names).not.toContain(absent)
		}
		expect(new Set(names).size).toBe(names.length)
		expect(variablesForTrigger("portal_case_closed")).toEqual(variablesForTrigger("portal_digest"))
	})

	it("offer the portal's snippets", () => {
		expect(snippetsForTrigger("portal_waiting_on_you")).toBe(PORTAL_SNIPPETS)
		expect(PORTAL_SNIPPETS.map(s => s.source).join("\n")).toContain("{% for item in items %}")
		expect(snippetsForTrigger("alert_created")).not.toBe(PORTAL_SNIPPETS)
	})
})
