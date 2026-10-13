import type { UbaIncidentVerdict } from "@/types/uba"
import { describe, expect, it } from "vitest"
import { incidentNeedsAttention } from "../utils"

function incident(status: UbaIncidentVerdict["status"], verdict: UbaIncidentVerdict["verdict"] = null): UbaIncidentVerdict {
	return { status, incident_alert_id: 42, verdict, message: "" }
}

describe("incidentNeedsAttention (#1239)", () => {
	it("stays quiet when the verdict reached the incident alert, or there is none", () => {
		expect(incidentNeedsAttention(incident("recorded", "FALSE_POSITIVE"), "FALSE_POSITIVE")).toBe(false)
		expect(incidentNeedsAttention(incident("not_linked"), "TRUE_POSITIVE")).toBe(false)
	})

	it("stays quiet when the incident alert already agrees", () => {
		expect(incidentNeedsAttention(incident("already_set", "TRUE_POSITIVE"), "TRUE_POSITIVE")).toBe(false)
	})

	it("warns when the incident alert disagrees, or the write-back was skipped or failed", () => {
		expect(incidentNeedsAttention(incident("already_set", "TRUE_POSITIVE"), "FALSE_POSITIVE")).toBe(true)
		expect(incidentNeedsAttention(incident("skipped"), "FALSE_POSITIVE")).toBe(true)
		expect(incidentNeedsAttention(incident("failed"), "TRUE_POSITIVE")).toBe(true)
	})
})
