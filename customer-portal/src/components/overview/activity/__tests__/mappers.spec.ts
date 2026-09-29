import type { OverviewAlert, OverviewCase } from "@/types/portal"
import { describe, expect, it } from "vitest"
import { alertToActivityItem, caseToActivityItem } from "../mappers"

const alert: OverviewAlert = {
	id: 7,
	alert_name: "Suspicious login",
	alert_description: "Suspicious login",
	status: "IN_PROGRESS",
	alert_creation_time: "2026-09-01T12:00:00.000Z",
	source: "wazuh",
	customer_code: "ACME",
	asset_names: ["web-01", "web-02", "db-01"]
}

const caseItem: OverviewCase = {
	id: 3,
	case_name: "Phishing wave",
	case_description: "Several users clicked the same link",
	case_status: "OPEN",
	case_creation_time: "2026-09-01T12:00:00.000Z",
	assigned_to: null,
	customer_code: "ACME",
	alert_count: 1
}

describe("overview mappers (light projections from /customer_portal/overview)", () => {
	it("alert: first asset plus how many more, status and source", () => {
		const item = alertToActivityItem(alert, { showCustomer: false })
		expect(item.meta).toEqual(["wazuh", "web-01 +2"])
		expect(item.status.label).toBe("in progress")
		expect(item.time).toBe(alert.alert_creation_time)
	})

	it("alert: the description is shown only when it says more than the name", () => {
		expect(alertToActivityItem(alert, { showCustomer: false }).detail).toBeUndefined()
		expect(
			alertToActivityItem({ ...alert, alert_description: "Seen from a new country" }, { showCustomer: false })
				.detail
		).toBe("Seen from a new country")
	})

	it("alert: the customer appears only when the user sees several", () => {
		expect(alertToActivityItem(alert, { showCustomer: true }).meta).toContain("ACME")
		expect(alertToActivityItem({ ...alert, asset_names: [] }, { showCustomer: false }).meta).toEqual(["wazuh"])
	})

	it("case: assignee or 'unassigned', and the linked alert count from alert_count", () => {
		expect(caseToActivityItem(caseItem, { showCustomer: false }).meta).toEqual(["unassigned", "1 alert"])
		expect(
			caseToActivityItem({ ...caseItem, assigned_to: "analyst1", alert_count: 3 }, { showCustomer: false }).meta
		).toEqual(["analyst1", "3 alerts"])
		expect(caseToActivityItem({ ...caseItem, alert_count: 0 }, { showCustomer: false }).meta).toEqual([
			"unassigned"
		])
	})
})
