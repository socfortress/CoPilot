import type { EventSearchState } from "@/types/siem"
import { describe, expect, it } from "vitest"
import { describeTime, emptyMemory } from "../eventSearchMemory"

const RELATIVE: EventSearchState = {
	source_name: "Wazuh",
	query: "",
	time_mode: "relative",
	time_amount: 24,
	time_unit: "h",
	time_from: null,
	time_to: null,
	page_size: 50
}

describe("eventSearchMemory", () => {
	it("starts empty", () => {
		expect(emptyMemory()).toEqual({ saved: [], recent: [], columns: {} })
	})

	it("describes a relative range in words, singular and plural", () => {
		expect(describeTime(RELATIVE, String)).toBe("last 24 hours")
		expect(describeTime({ ...RELATIVE, time_amount: 1, time_unit: "d" }, String)).toBe("last 1 day")
		expect(describeTime({ ...RELATIVE, time_amount: 2, time_unit: "w" }, String)).toBe("last 2 weeks")
	})

	it("describes an absolute range with the given formatter", () => {
		const state: EventSearchState = {
			...RELATIVE,
			time_mode: "absolute",
			time_from: "2026-10-01T06:00:00Z",
			time_to: "2026-10-01T08:00:00Z"
		}
		expect(describeTime(state, iso => iso.slice(11, 16))).toBe("06:00 → 08:00")
	})
})
