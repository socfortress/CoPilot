import type { AiInsightAlert } from "@/types/aiReports"
import type { OverviewAlert, OverviewCase } from "@/types/portal"
import { describe, expect, it } from "vitest"
import { alertToActivityItem, caseToActivityItem, findingToActivityItem } from "../mappers"

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
		const item = alertToActivityItem(alert, {})
		expect(item.meta).toEqual(["wazuh", "web-01 +2"])
		expect(item.status.label).toBe("in progress")
		expect(item.time).toBe(alert.alert_creation_time)
	})

	it("alert: the description is shown only when it says more than the name", () => {
		expect(alertToActivityItem(alert, {}).detail).toBeUndefined()
		expect(alertToActivityItem({ ...alert, alert_description: "Seen from a new country" }, {}).detail).toBe(
			"Seen from a new country"
		)
	})

	it("alert: the customer appears, by name, only when the user sees several", () => {
		const customerLabel = (code: string) => (code === "ACME" ? "Acme Rome" : code)
		expect(alertToActivityItem(alert, { customerLabel }).meta).toEqual(["wazuh", "web-01 +2", "Acme Rome"])
		expect(alertToActivityItem({ ...alert, asset_names: [] }, {}).meta).toEqual(["wazuh"])
	})

	it("case and finding: named by the same label, and only when one is given", () => {
		const customerLabel = () => "Acme Rome"
		expect(caseToActivityItem(caseItem, { customerLabel }).meta).toEqual(["unassigned", "1 alert", "Acme Rome"])
		const finding = {
			alert_id: 1,
			alert_name: "x",
			customer_code: "ACME",
			severity_assessment: "High",
			summary: null,
			report_created_at: "2026-09-01T12:00:00.000Z"
		} as unknown as AiInsightAlert
		expect(findingToActivityItem(finding, { customerLabel }).meta).toEqual(["Acme Rome"])
		expect(findingToActivityItem(finding, {}).meta).toEqual([])
	})

	it("case: assignee or 'unassigned', and the linked alert count from alert_count", () => {
		expect(caseToActivityItem(caseItem, {}).meta).toEqual(["unassigned", "1 alert"])
		expect(caseToActivityItem({ ...caseItem, assigned_to: "analyst1", alert_count: 3 }, {}).meta).toEqual([
			"analyst1",
			"3 alerts"
		])
		expect(caseToActivityItem({ ...caseItem, alert_count: 0 }, {}).meta).toEqual(["unassigned"])
	})
})
