/**
 * The "What Talon sees" panel's words and rows, and its request. The states it shows are in
 * `CustomerKnowledgeSees.spec.ts`.
 */
import type { TalonMemoryFailureCode } from "@/api/endpoints/talonMemory"
import type { TalonSeesSource } from "@/types/customer-knowledge"
import { beforeEach, describe, expect, it, vi } from "vitest"
import customerKnowledge from "@/api/endpoints/customer-knowledge"
import {
	carriedLine,
	CATEGORIES,
	categoryLabel,
	coverageRows,
	eventsLine,
	fieldRows,
	fieldsLine,
	isUnsupported,
	measuredLine,
	NO_PROFILE_TEXT,
	NO_SOURCES_TEXT,
	NO_TENANT_MAP_TEXT,
	NO_VERIFIED_SOURCES_TEXT,
	NOT_MEASURED_ABOUT,
	sourceView,
	UNSUPPORTED_TEXT
} from "../sees"

const get = vi.fn()

vi.mock("@/api/http-client", () => ({ HttpClient: { get: (...a: unknown[]) => get(...a) } }))

const SOURCE: TalonSeesSource = {
	pattern: "wazuh-lab_*",
	categories: ["endpoint", "waf"],
	events: 3400000,
	degraded: false,
	measured_at: "2026-11-06T05:30:00+00:00",
	fields: { host: ["agent_name"], user: ["data_win_eventdata_user"] }
}

const when = (moment: string) => moment

function failure(code: TalonMemoryFailureCode) {
	return { status: 404, code, detail: "x" }
}

describe("the words", () => {
	it("says the panel is measured from logs, and when", () => {
		const line = measuredLine("2026-11-06T05:30:00+00:00", moment => `at ${moment}`)
		expect(line).toContain("Measured daily from this customer's logs")
		expect(line).toContain("Last measured at 2026-11-06T05:30:00+00:00.")
	})

	it("leaves out the time it doesn't have", () => {
		const when = vi.fn()
		expect(measuredLine(null, when)).not.toContain("Last measured")
		expect(when).not.toHaveBeenCalled()
	})

	it.each([
		["measured", measuredLine("2026-11-06", moment => moment)],
		["no profile", NO_PROFILE_TEXT],
		["no tenant map", NO_TENANT_MAP_TEXT],
		["no verified sources", NO_VERIFIED_SOURCES_TEXT],
		["unsupported", UNSUPPORTED_TEXT],
		["not measured", NOT_MEASURED_ABOUT],
		["no sources", NO_SOURCES_TEXT]
	])("never says Talon reads the SOC's facts: %s", (_name, text) => {
		expect(text).not.toMatch(/fact/i)
		expect(text).not.toMatch(/reads? (these|the|your)/i)
	})

	it("words the states as asked", () => {
		expect(NO_PROFILE_TEXT).toContain("Talon hasn't measured this customer's log sources in the last 7 days.")
		expect(NO_PROFILE_TEXT).toContain("source_profile")
		expect(NO_TENANT_MAP_TEXT).toContain("tenant map")
		expect(NO_TENANT_MAP_TEXT).toContain("an investigation wouldn't see")
	})

	it("counts events over the window", () => {
		const count = (3400000).toLocaleString()
		expect(eventsLine(3400000, 7)).toBe(`${count} events in the last 7 days`)
		expect(eventsLine(3400000, null)).toBe(`${count} events`)
		expect(eventsLine(3400000, 1)).toBe(`${count} events in the last day`)
		expect(eventsLine(1, 7)).toBe("1 event in the last 7 days")
		expect(eventsLine(0, 7)).toBe("0 events in the last 7 days")
	})

	it("doesn't turn an unknown count into zero", () => {
		expect(eventsLine(null, 7)).toBeNull()
	})

	it("says the window the fields are from", () => {
		expect(fieldsLine(30)).toContain("Fields seen in the last 30 days.")
		expect(fieldsLine(1)).toContain("Fields seen in the last day.")
		expect(fieldsLine(null)).not.toContain("Fields seen")
	})

	it("says an investigation gets fewer fields than this list, with or without the window", () => {
		expect(fieldsLine(30)).toContain("An investigation gets a shorter list")
		expect(fieldsLine(null)).toContain("An investigation gets a shorter list")
	})
})

describe("coverage", () => {
	it("has one row per category, in order, each with its state's word", () => {
		const rows = coverageRows({ available: ["endpoint", "email"], degraded: ["identity"], unavailable: ["network", "waf"] })
		expect(rows.map(row => [row.category, row.label, row.word])).toEqual([
			["endpoint", "Endpoint", "Available"],
			["identity", "Identity", "Quiet"],
			["email", "Email", "Available"],
			["network", "Network", "None"],
			["cloud", "Cloud", "Not measured"],
			["waf", "WAF", "None"]
		])
	})

	it("claims nothing about a category in no state", () => {
		const rows = coverageRows({ available: [], degraded: [], unavailable: [] })
		expect(rows).toHaveLength(CATEGORIES.length)
		expect(rows.every(row => row.state === "not_measured" && row.word === "Not measured")).toBe(true)
	})

	it("claims nothing at all without a coverage", () => {
		expect(coverageRows(null).every(row => row.state === "not_measured")).toBe(true)
	})

	it("takes the weaker claim for a category listed twice", () => {
		const rows = coverageRows({ available: ["endpoint", "email"], degraded: ["endpoint"], unavailable: ["email"] })
		expect(rows.find(row => row.category === "endpoint")?.state).toBe("degraded")
		expect(rows.find(row => row.category === "email")?.state).toBe("unavailable")
	})

	it("labels a category it doesn't know as itself", () => {
		expect(categoryLabel("waf")).toBe("WAF")
		expect(categoryLabel("printers" as never)).toBe("printers")
	})
})

describe("a log source", () => {
	it("is shown with friendly labels", () => {
		const view = sourceView(SOURCE, 7, SOURCE.measured_at, when)
		expect(view.pattern).toBe("wazuh-lab_*")
		expect(view.categories).toEqual(["Endpoint", "WAF"])
		expect(view.events).toBe(`${(3400000).toLocaleString()} events in the last 7 days`)
		expect(view.fields).toEqual([
			{ role: "user", label: "User", names: ["data_win_eventdata_user"] },
			{ role: "host", label: "Host", names: ["agent_name"] }
		])
	})

	it.each([
		[true, true],
		[false, false],
		[null, false]
	])("marks degraded %s as quiet: %s", (degraded, quiet) => {
		expect(sourceView({ ...SOURCE, degraded }, 7, null, when).quiet).toBe(quiet)
	})

	it("says nothing about its time when it is the run's", () => {
		expect(sourceView(SOURCE, 7, SOURCE.measured_at, when).carried).toBeNull()
	})

	it("says when its numbers are older than the run: a failed source keeps its last good row", () => {
		const carried = sourceView({ ...SOURCE, measured_at: "2026-10-31T05:30:00+00:00" }, 7, SOURCE.measured_at, when)
		expect(carried.carried).toContain("2026-10-31T05:30:00+00:00")
		expect(carried.events).toContain("in the last 7 days")
	})

	it("compares times, not their spelling", () => {
		expect(carriedLine("2026-11-06T05:30:00Z", "2026-11-06T05:30:00+00:00", when)).toBeNull()
	})

	it.each([
		[null, "2026-11-06T05:30:00+00:00"],
		["2026-10-31T05:30:00+00:00", null],
		["nonsense", "2026-11-06T05:30:00+00:00"]
	])("claims nothing about a time it can't compare: %s against %s", (measuredAt, runAt) => {
		expect(carriedLine(measuredAt, runAt, when)).toBeNull()
	})

	it("has a label for every role", () => {
		const roles = [
			["src_ip", "Source IP"],
			["dst_ip", "Destination IP"],
			["user", "User"],
			["host", "Host"],
			["process", "Process"],
			["command_line", "Command line"],
			["file_hash", "File hash"],
			["file_path", "File path"],
			["url", "URL"],
			["domain", "Domain"],
			["email", "Email"],
			["action", "Action"]
		] as const
		const fields = Object.fromEntries(roles.map(([role]) => [role, ["x"]]))
		expect(fieldRows(fields).map(row => [row.role, row.label])).toEqual(roles.map(([role, label]) => [role, label]))
	})

	it("skips an empty role and one it doesn't know", () => {
		expect(fieldRows({ host: [], url: ["u"], printer: ["p"] } as never).map(row => row.role)).toEqual(["url"])
	})
})

describe("what counts as unsupported", () => {
	it.each(["unsupported", "v2_off"] as const)("%s is a quiet note", code => {
		expect(isUnsupported(failure(code))).toBe(true)
	})

	it.each(["unavailable", "bad_answer", "invalid", "forbidden", "unknown_customer", "unknown"] as const)(
		"%s is a failure",
		code => {
			expect(isUnsupported(failure(code))).toBe(false)
		}
	)

	it("is nothing without a failure", () => {
		expect(isUnsupported(null)).toBe(false)
	})
})

describe("the request", () => {
	beforeEach(() => {
		get.mockReset().mockResolvedValue({ data: {} })
	})

	it("asks for the customer's knowledge route with the caller's signal", async () => {
		const { signal } = new AbortController()
		await customerKnowledge.whatTalonSees("ACME", signal)
		expect(get).toHaveBeenCalledWith("/talon/knowledge/ACME", { signal })
	})

	it("encodes the customer code", async () => {
		await customerKnowledge.whatTalonSees("a/b c")
		expect(get.mock.calls[0]?.[0]).toBe("/talon/knowledge/a%2Fb%20c")
	})
})
