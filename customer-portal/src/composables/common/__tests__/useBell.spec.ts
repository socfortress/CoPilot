import type { PortalNotification } from "@/types/notifications"
import { describe, expect, it, vi } from "vitest"
import { serverId, toBellItem } from "../useBell"

vi.mock("@/api", () => ({ default: {} }))
vi.mock("@/router", () => ({ default: { push: vi.fn() } }))

function notification(fields: Partial<PortalNotification>): PortalNotification {
	return {
		id: 7,
		customer_code: "ACME",
		event: "alert_created",
		entity_type: "alert",
		entity_id: 42,
		title: "New High alert: Odd login",
		body: "From an unusual country.",
		severity: "High",
		created_at: "2026-10-01T08:15:00",
		read: false,
		...fields
	}
}

/** A server notification as the bell shows it (#1282). */
describe("toBellItem", () => {
	it("opens the alert, coloured by its severity", () => {
		const item = toBellItem(notification({}))
		expect(item).toMatchObject({
			id: "server-7",
			category: "alert",
			type: "error",
			title: "New High alert: Odd login",
			description: "From an unusual country.",
			read: false,
			icon: "carbon:warning-alt",
			actionRoute: { name: "AlertDetails", params: { id: "42" } },
			actionTitle: "Open alert"
		})
		expect(toBellItem(notification({ severity: "Medium" })).type).toBe("warning")
	})

	it("reads the stored time as UTC, never as local time", () => {
		expect((toBellItem(notification({})).date as Date).toISOString()).toBe("2026-10-01T08:15:00.000Z")
	})

	it("opens the case or the reports, with their own icons", () => {
		const waiting = toBellItem(notification({ event: "waiting_on_you", entity_type: "case", entity_id: 3 }))
		expect(waiting).toMatchObject({
			type: "warning",
			icon: "carbon:user-follow",
			actionRoute: { name: "CaseDetails", params: { id: "3" } }
		})
		const report = toBellItem(notification({ event: "report_ready", entity_type: "report", body: null }))
		expect(report).toMatchObject({
			type: "success",
			category: "report",
			description: "",
			actionRoute: { name: "ReportsList" },
			actionTitle: "View reports"
		})
	})

	it("tells a server item from a session one", () => {
		expect(serverId("server-12")).toBe(12)
		expect(serverId("report-12")).toBeNull()
		expect(serverId(12)).toBeNull()
	})
})
