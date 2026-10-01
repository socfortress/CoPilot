import { describe, expect, it } from "vitest"
import { buildPostureCells } from "../postureCells"

describe("posture cells", () => {
	it("break a total down into every status, waiting on the customer included (#1187)", () => {
		const counts = { total: 10, open: 3, in_progress: 2, pending_customer: 1, closed: 4 }
		const [alerts] = buildPostureCells({
			alerts: counts,
			cases: { ...counts },
			agents: { total: 1, online: 1, offline: 0, critical: 0 }
		})
		const segments = alerts!.segments
		expect(segments.map(segment => segment.label)).toEqual(["open", "in progress", "waiting on you", "closed"])
		// The bar and its legend add up to the footnote's total.
		expect(segments.reduce((sum, segment) => sum + segment.value, 0)).toBe(counts.total)
		expect(alerts!.footnote).toBe("10 total")
	})
})
