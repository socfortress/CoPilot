/**
 * The run view (talon-analyst §5.4): spans nested by parent and ordered by start, bars placed by
 * start and duration, model or tool, tokens and ERROR; the truncated, dropped, empty and 409 states;
 * and only the DTO's own fields, as text: extra properties a fixture carries (`attributes`,
 * `status_message`, `input`, …) are never rendered, and markup in a name is shown, not run.
 */
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import TalonRunTimeline from "../TalonRunTimeline.vue"
import { JOB, refused, span, timeline } from "./fixtures"

const getRunTimeline = vi.fn()

vi.mock("@/api", () => ({
	default: { talonUsage: { getRunTimeline: (...a: unknown[]) => getRunTimeline(...a) } }
}))

const MARKER = "PLANTED-MARKER-7f3a"

function render() {
	return mount(TalonRunTimeline, { props: { jobId: JOB } })
}

const SPANS = [
	span("000000000000000c", {
		parent_id: "000000000000000a",
		kind: "TOOL",
		name: "execute_tool siem_search",
		tool: "siem_search",
		start_time: "2026-10-16T08:00:05.000000Z",
		end_time: "2026-10-16T08:00:10.000000Z",
		duration_ms: 5000,
		status_code: "ERROR"
	}),
	span("000000000000000a"),
	span("000000000000000b", {
		parent_id: "000000000000000a",
		kind: "LLM",
		name: "chat claude-sonnet-5-5",
		model: "claude-sonnet-5-5",
		start_time: "2026-10-16T08:00:01.000000Z",
		end_time: "2026-10-16T08:00:03.500000Z",
		duration_ms: 2500,
		prompt_tokens: 1200,
		completion_tokens: 300,
		total_tokens: 1500
	})
]

enableAutoUnmount(afterEach)

describe("talon run timeline", () => {
	beforeEach(() => {
		getRunTimeline.mockReset()
	})

	it("nests by parent, orders by start, and places each bar by start and duration", async () => {
		getRunTimeline.mockResolvedValue({ data: timeline(SPANS) })
		const wrapper = render()
		await flushPromises()
		expect(getRunTimeline).toHaveBeenCalledWith(JOB, expect.any(AbortSignal))
		expect(wrapper.get('[data-testid="talon-run-lane-label"]').text()).toBe("Trace 1 · S5")
		const rows = wrapper.findAll('[data-testid="talon-run-span"]')
		expect(rows.map(r => [r.attributes("data-span-id"), r.attributes("data-depth")])).toEqual([
			["000000000000000a", "0"],
			["000000000000000b", "1"],
			["000000000000000c", "1"]
		])
		const bars = wrapper.findAll('[data-testid="talon-run-span-bar"]').map(b => b.attributes("style"))
		expect(bars[0]).toContain("left: 0%")
		expect(bars[0]).toContain("width: 100%")
		expect(bars[1]).toContain("left: 10%")
		expect(bars[1]).toContain("width: 25%")
		expect(bars[2]).toContain("left: 50%")
		expect(bars[2]).toContain("width: 50%")
		expect(rows[1].get('[data-testid="talon-run-span-subject"]').text()).toBe("claude-sonnet-5-5")
		expect(rows[1].get('[data-testid="talon-run-span-tokens"]').text()).toBe("1,200 in · 300 out")
		expect(rows[2].get('[data-testid="talon-run-span-subject"]').text()).toBe("siem_search")
		expect(rows[2].find('[data-testid="talon-run-span-error"]').exists()).toBe(true)
		expect(rows[1].find('[data-testid="talon-run-span-error"]').exists()).toBe(false)
		expect(wrapper.find('[data-testid="talon-run-cost-note"]').exists()).toBe(true)
		expect(wrapper.find('[data-testid="talon-run-truncated"]').exists()).toBe(false)
		expect(wrapper.find('[data-testid="talon-run-dropped"]').exists()).toBe(false)
	})

	it("never renders a property the DTO doesn't name", async () => {
		const hostile = span("000000000000000d", {
			attributes: { "input.value": MARKER, "output.value": MARKER },
			status_message: MARKER,
			input: MARKER,
			output: MARKER,
			events: [{ name: MARKER }],
			"llm.input_messages": MARKER
		} as never)
		getRunTimeline.mockResolvedValue({ data: { ...timeline([hostile]), extra: MARKER } })
		const wrapper = render()
		await flushPromises()
		expect(wrapper.findAll('[data-testid="talon-run-span"]')).toHaveLength(1)
		expect(wrapper.html()).not.toContain(MARKER)
	})

	it("shows markup in a name as text", async () => {
		const name = `<img src=x onerror="window.__pwned=1"><b>bold</b>`
		getRunTimeline.mockResolvedValue({
			data: timeline([span("000000000000000e", { name, model: "<script>x</script>" })])
		})
		const wrapper = render()
		await flushPromises()
		expect(wrapper.get('[data-testid="talon-run-span-name"]').text()).toBe(name)
		expect(wrapper.find("img").exists()).toBe(false)
		expect(wrapper.find("b").exists()).toBe(false)
		expect(wrapper.find("script").exists()).toBe(false)
		expect(wrapper.html()).toContain("&lt;img")
	})

	it("says when spans were cut or left out", async () => {
		getRunTimeline.mockResolvedValue({ data: timeline(SPANS, { truncated: true, dropped: 2 }) })
		const wrapper = render()
		await flushPromises()
		expect(wrapper.find('[data-testid="talon-run-truncated"]').exists()).toBe(true)
		expect(wrapper.get('[data-testid="talon-run-dropped"]').text()).toContain("2 span(s) left out")
	})

	it("no trace data: the empty state", async () => {
		getRunTimeline.mockResolvedValue({ data: timeline([], { note: "no trace data" }) })
		const wrapper = render()
		await flushPromises()
		expect(wrapper.get('[data-testid="talon-run-empty"]').text()).toBe("No trace data for this run.")
		expect(wrapper.find('[data-testid="talon-run-lane"]').exists()).toBe(false)
	})

	it("409: no run view for this customer", async () => {
		getRunTimeline.mockRejectedValue(refused(409, "this customer's runs are not traced to a project of its own"))
		const wrapper = render()
		await flushPromises()
		expect(wrapper.get('[data-testid="talon-run-no-project"]').text()).toContain("No run view for this customer")
		expect(wrapper.find('[data-testid="talon-run-span"]').exists()).toBe(false)
	})

	it("phoenix failing shows the fixed text", async () => {
		getRunTimeline.mockRejectedValue(refused(502, "Phoenix request failed"))
		const wrapper = render()
		await flushPromises()
		expect(wrapper.get('[data-testid="talon-run-error"]').text()).toBe("Phoenix request failed")
	})
})
