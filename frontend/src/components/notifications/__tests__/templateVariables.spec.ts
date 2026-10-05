import { describe, expect, it } from "vitest"
import { INTERNAL_TRIGGERS, isInternalTrigger, NOTIFICATION_TRIGGER_LABELS, SLA_TRIGGERS } from "@/types/notifications"
import { variablesForTrigger } from "../templateVariables"

describe("sLA notification triggers", () => {
	it("are internal-only and labelled", () => {
		for (const trigger of SLA_TRIGGERS) {
			expect(INTERNAL_TRIGGERS).toContain(trigger)
			expect(isInternalTrigger(trigger)).toBe(true)
		}
		expect(NOTIFICATION_TRIGGER_LABELS.sla_at_risk).toBe("SLA at risk")
		expect(NOTIFICATION_TRIGGER_LABELS.sla_breached).toBe("SLA breached")
		expect(isInternalTrigger("ai_report_reviewed")).toBe(false)
	})

	it("advertise the SLA context, not the alert or assignment extras", () => {
		const names = variablesForTrigger("sla_breached").map(v => v.name)
		expect(names).toEqual(
			expect.arrayContaining(["context.clock", "context.due_at", "context.overdue_minutes", "assignee"])
		)
		expect(names).not.toContain("context.asset_name")
		expect(names).not.toContain("actor")
	})

	it("list every variable once when no trigger is picked", () => {
		const names = variablesForTrigger(null).map(v => v.name)
		expect(new Set(names).size).toBe(names.length)
		expect(names).toContain("context.remaining_minutes")
	})
})
