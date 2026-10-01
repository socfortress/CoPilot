import { describe, expect, it } from "vitest"
import { periodParams, scopeParams } from "../endpoints/soc-management"

describe("soc management request params", () => {
	it("drops empty filters: an absent filter means all, never none", () => {
		expect(scopeParams({ customerCodes: [], severities: ["High"], sources: undefined })).toEqual({
			severities: ["High"]
		})
		expect(scopeParams({ customerCodes: ["ACME"], sources: ["wazuh"] })).toEqual({
			customer_codes: ["ACME"],
			sources: ["wazuh"]
		})
	})

	it("sends the period as UTC instants", () => {
		expect(
			periodParams({ dateFrom: new Date("2026-09-01T00:00:00Z"), dateTo: new Date("2026-10-01T00:00:00Z") })
		).toEqual({
			date_from: "2026-09-01T00:00:00.000Z",
			date_to: "2026-10-01T00:00:00.000Z"
		})
	})
})
