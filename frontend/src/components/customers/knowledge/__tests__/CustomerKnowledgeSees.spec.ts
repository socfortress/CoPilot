/**
 * The "What Talon sees" panel: each state, the retry and a customer change. Its words and rows are
 * in `sees.spec.ts`.
 */
import type { TalonSees } from "@/types/customer-knowledge"
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils"
import { AxiosError, AxiosHeaders, CanceledError } from "axios"
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"
import CustomerKnowledgeSees from "../CustomerKnowledgeSees.vue"
import { NO_PROFILE_TEXT, NO_TENANT_MAP_TEXT, NO_VERIFIED_SOURCES_TEXT, UNSUPPORTED_TEXT } from "../sees"

const whatTalonSees = vi.fn()

vi.mock("@/api", () => ({ default: { customerKnowledge: { whatTalonSees: (...a: unknown[]) => whatTalonSees(...a) } } }))

const MEASURED = "2026-11-06T05:30:00+00:00"

function answer(overrides: Partial<TalonSees> = {}): { data: TalonSees } {
	return {
		data: {
			success: true,
			customer_code: "ACME",
			status: "ok",
			measured_at: MEASURED,
			field_days: 30,
			event_days: 7,
			coverage: { available: ["endpoint", "email"], degraded: ["identity"], unavailable: ["network", "waf"] },
			sources: [
				{
					pattern: "o365-lab_*",
					categories: ["email", "identity"],
					events: 0,
					degraded: true,
					measured_at: MEASURED,
					fields: { email: ["data_o365_user"] }
				},
				{
					pattern: "wazuh-lab_*",
					categories: ["endpoint"],
					events: 3400000,
					degraded: false,
					measured_at: MEASURED,
					fields: { host: ["agent_name"], command_line: ["data_cmd", "data_win_cmd"] }
				}
			],
			not_measured: ["fortinet-lab_*"],
			...overrides
		}
	}
}

function empty(status: TalonSees["status"]) {
	return answer({
		status,
		measured_at: null,
		field_days: null,
		event_days: null,
		coverage: null,
		sources: [],
		not_measured: []
	})
}

function refusal(status: number, data: unknown) {
	const headers = new AxiosHeaders()
	return new AxiosError("x", "ERR", undefined, undefined, { status, statusText: "", data, headers, config: { headers } })
}

/** A request that settles when the test says so, and rejects as axios does when it is aborted. */
function pending() {
	let resolve!: (value: unknown) => void
	let reject!: (reason: unknown) => void
	const promise = new Promise((res, rej) => {
		resolve = res
		reject = rej
	})
	return { promise, resolve, reject }
}

async function render(customerCode = "ACME") {
	const wrapper = mount(CustomerKnowledgeSees, { props: { customerCode }, global: { stubs: { Icon: true } } })
	await flushPromises()
	return wrapper
}

type Panel = Awaited<ReturnType<typeof render>>

function byId(wrapper: Panel, id: string) {
	return wrapper.find(`[data-testid="${id}"]`)
}

function signalOf(call: number): AbortSignal {
	return whatTalonSees.mock.calls[call]?.[1] as AbortSignal
}

enableAutoUnmount(afterEach)

beforeEach(() => {
	setActivePinia(createPinia())
	whatTalonSees.mockReset().mockResolvedValue(answer())
})

describe("the states", () => {
	it("says it is reading while the request is out", async () => {
		const request = pending()
		whatTalonSees.mockReturnValue(request.promise)
		const wrapper = await render()
		expect(wrapper.text()).toContain("What Talon sees")
		expect(byId(wrapper, "knowledge-sees-loading").exists()).toBe(true)
		expect(byId(wrapper, "knowledge-sees-measured").exists()).toBe(false)
		request.resolve(answer())
		await flushPromises()
		expect(byId(wrapper, "knowledge-sees-loading").exists()).toBe(false)
		expect(byId(wrapper, "knowledge-sees-measured").exists()).toBe(true)
	})

	it("says what it measured, and when, in the viewer's date format", async () => {
		const wrapper = await render()
		const formats = useSettingsStore().dateFormat
		const line = byId(wrapper, "knowledge-sees-when").text()
		expect(line).toContain("Measured daily from this customer's logs")
		expect(line).toContain(String(formatDate(MEASURED, formats.datetime)))
	})

	it("shows one row per category, with Not measured for a category in no state", async () => {
		const wrapper = await render()
		const row = (category: string) => byId(wrapper, `knowledge-sees-coverage-${category}`).text()
		expect(row("endpoint")).toBe("EndpointAvailable")
		expect(row("identity")).toBe("IdentityQuiet")
		expect(row("network")).toBe("NetworkNone")
		expect(row("waf")).toBe("WAFNone")
		expect(row("cloud")).toBe("CloudNot measured")
	})

	it("shows each log source with its pattern, categories, events and field roles", async () => {
		const wrapper = await render()
		const [quiet, wazuh] = wrapper.findAll('[data-testid="knowledge-sees-source"]')
		expect(wazuh?.get('[data-testid="knowledge-sees-source-pattern"]').text()).toBe("wazuh-lab_*")
		expect(wazuh?.get('[data-testid="knowledge-sees-source-pattern"]').classes()).toContain("font-mono")
		expect(wazuh?.text()).toContain("Endpoint")
		expect(wazuh?.get('[data-testid="knowledge-sees-source-events"]').text()).toBe(
			`${(3400000).toLocaleString()} events in the last 7 days`
		)
		expect(wazuh?.get('[data-testid="knowledge-sees-field-host"]').text()).toBe("Host:agent_name")
		expect(wazuh?.get('[data-testid="knowledge-sees-field-command_line"]').text()).toBe("Command line:data_cmddata_win_cmd")
		expect(wazuh?.find('[data-testid="knowledge-sees-source-quiet"]').exists()).toBe(false)
		expect(quiet?.get('[data-testid="knowledge-sees-source-quiet"]').text()).toBe("Quiet")
		expect(quiet?.text()).toContain("Email, Identity")
		expect(quiet?.text()).toContain("0 events in the last 7 days")
	})

	it("says the window the fields are from", async () => {
		expect((await render()).text()).toContain("Fields seen in the last 30 days.")
	})

	it("lists the patterns it couldn't measure", async () => {
		const wrapper = await render()
		expect(byId(wrapper, "knowledge-sees-not-measured").text()).toContain("fortinet-lab_*")
	})

	it("hides the not measured block when there's nothing in it", async () => {
		whatTalonSees.mockResolvedValue(answer({ not_measured: [] }))
		expect(byId(await render(), "knowledge-sees-not-measured").exists()).toBe(false)
	})

	it("reads an ok answer with nothing in it", async () => {
		whatTalonSees.mockResolvedValue(
			answer({ measured_at: null, field_days: null, event_days: null, coverage: null, sources: [], not_measured: [] })
		)
		const wrapper = await render()
		expect(byId(wrapper, "knowledge-sees-no-sources").exists()).toBe(true)
		expect(byId(wrapper, "knowledge-sees-when").text()).not.toContain("Last measured")
		expect(byId(wrapper, "knowledge-sees-coverage-endpoint").text()).toContain("Not measured")
		expect(wrapper.text()).not.toContain("Fields seen")
	})

	it("doesn't state a count Talon didn't report", async () => {
		const sources = answer().data.sources.map(source => ({ ...source, events: null }))
		whatTalonSees.mockResolvedValue(answer({ sources }))
		expect(byId(await render(), "knowledge-sees-source-events").exists()).toBe(false)
	})

	it("says when Talon hasn't measured this customer", async () => {
		whatTalonSees.mockResolvedValue(empty("no_profile"))
		const wrapper = await render()
		expect(byId(wrapper, "knowledge-sees-no-profile").text()).toBe(NO_PROFILE_TEXT)
		expect(byId(wrapper, "knowledge-sees-measured").exists()).toBe(false)
		expect(byId(wrapper, "knowledge-sees-failure").exists()).toBe(false)
	})

	it("says when the gap is Talon's tenant map, rather than six kinds of log it has none of", async () => {
		whatTalonSees.mockResolvedValue(empty("no_sources"))
		const wrapper = await render()
		expect(byId(wrapper, "knowledge-sees-no-verified-sources").text()).toBe(NO_VERIFIED_SOURCES_TEXT)
		expect(byId(wrapper, "knowledge-sees-measured").exists()).toBe(false)
	})

	it("marks a source the last run couldn't measure, and only that one", async () => {
		const [quiet, wazuh] = answer().data.sources
		const older = { ...wazuh, measured_at: "2026-10-31T05:30:00+00:00" }
		whatTalonSees.mockResolvedValue(answer({ sources: [quiet, older] }))
		const wrapper = await render()
		const marks = wrapper.findAll('[data-testid="knowledge-sees-source-carried"]')
		expect(marks).toHaveLength(1)
		expect(marks[0].text()).toContain("These numbers are from")
	})

	it("says an investigation gets fewer fields than this list", async () => {
		whatTalonSees.mockResolvedValue(answer())
		expect(byId(await render(), "knowledge-sees-fields-note").text()).toContain("An investigation gets a shorter list")
	})

	it("says when Talon can't read its tenant map", async () => {
		whatTalonSees.mockResolvedValue(empty("no_tenant_map"))
		const wrapper = await render()
		expect(byId(wrapper, "knowledge-sees-no-tenant-map").text()).toBe(NO_TENANT_MAP_TEXT)
		expect(byId(wrapper, "knowledge-sees-measured").exists()).toBe(false)
	})

	it.each([
		["an older talon-analyst", 404, { detail: "This Talon has no knowledge API", code: "unsupported" }],
		["Talon v2 off in CoPilot, a bare 404", 404, { detail: "Not Found" }]
	])("is a quiet line for %s, not an error", async (_name, status, data) => {
		whatTalonSees.mockRejectedValue(refusal(status, data))
		const wrapper = await render()
		expect(byId(wrapper, "knowledge-sees-unsupported").text()).toBe(UNSUPPORTED_TEXT)
		expect(byId(wrapper, "knowledge-sees-failure").exists()).toBe(false)
		expect(byId(wrapper, "knowledge-sees").exists()).toBe(false)
	})

	it.each([
		[502, { detail: "Talon couldn't read what it has measured; try again shortly", code: "unavailable" }],
		[504, { detail: "Talon didn't answer in time; try again shortly", code: "unavailable" }],
		[502, { detail: "Talon's answer was not in the expected shape", code: "bad_answer" }],
		[404, { detail: "There is no such customer", code: "unknown_customer" }]
	])("is an alert with CoPilot's text for a %i", async (status, data) => {
		whatTalonSees.mockRejectedValue(refusal(status, data))
		const wrapper = await render()
		expect(byId(wrapper, "knowledge-sees-failure").text()).toContain(data.detail)
		expect(byId(wrapper, "knowledge-sees-unsupported").exists()).toBe(false)
	})

	it("is an alert when the network fails", async () => {
		whatTalonSees.mockRejectedValue(new Error("Network Error"))
		expect(byId(await render(), "knowledge-sees-failure").exists()).toBe(true)
	})
})

describe("trying again", () => {
	it("reads again, and shows the answer instead of the alert", async () => {
		whatTalonSees.mockRejectedValueOnce(refusal(502, { detail: "broken", code: "unavailable" }))
		const wrapper = await render()
		expect(byId(wrapper, "knowledge-sees-failure").exists()).toBe(true)
		await byId(wrapper, "knowledge-sees-retry").trigger("click")
		await flushPromises()
		expect(whatTalonSees).toHaveBeenCalledTimes(2)
		expect(byId(wrapper, "knowledge-sees-failure").exists()).toBe(false)
		expect(byId(wrapper, "knowledge-sees-measured").exists()).toBe(true)
	})

	it("shows the loading line instead of the alert while it reads", async () => {
		whatTalonSees.mockRejectedValueOnce(refusal(502, { detail: "broken", code: "unavailable" }))
		const wrapper = await render()
		whatTalonSees.mockReturnValue(pending().promise)
		await byId(wrapper, "knowledge-sees-retry").trigger("click")
		expect(byId(wrapper, "knowledge-sees-failure").exists()).toBe(false)
		expect(byId(wrapper, "knowledge-sees-loading").exists()).toBe(true)
	})

	it("stays an alert when it fails again", async () => {
		whatTalonSees.mockRejectedValue(refusal(502, { detail: "broken", code: "unavailable" }))
		const wrapper = await render()
		await byId(wrapper, "knowledge-sees-retry").trigger("click")
		await flushPromises()
		expect(byId(wrapper, "knowledge-sees-failure").text()).toContain("broken")
	})
})

describe("a customer change", () => {
	it("asks for the new customer, and passes each request its signal", async () => {
		const wrapper = await render()
		await wrapper.setProps({ customerCode: "GLOBEX" })
		await flushPromises()
		expect(whatTalonSees.mock.calls.map(call => call[0])).toEqual(["ACME", "GLOBEX"])
		expect(signalOf(0)).toBeInstanceOf(AbortSignal)
		expect(signalOf(1)).not.toBe(signalOf(0))
	})

	it("doesn't show the old customer's sources while the new ones load", async () => {
		const wrapper = await render()
		expect(wrapper.text()).toContain("wazuh-lab_*")
		whatTalonSees.mockReturnValue(pending().promise)
		await wrapper.setProps({ customerCode: "GLOBEX" })
		expect(wrapper.text()).not.toContain("wazuh-lab_*")
		expect(byId(wrapper, "knowledge-sees-loading").exists()).toBe(true)
	})

	it("aborts the old request", async () => {
		whatTalonSees.mockReturnValue(pending().promise)
		const wrapper = await render()
		await wrapper.setProps({ customerCode: "GLOBEX" })
		expect(signalOf(0).aborted).toBe(true)
		expect(signalOf(1).aborted).toBe(false)
	})

	it("never lets a stale answer replace a newer one", async () => {
		const first = pending()
		const second = pending()
		whatTalonSees.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise)
		const wrapper = await render()
		await wrapper.setProps({ customerCode: "GLOBEX" })
		second.resolve(answer({ customer_code: "GLOBEX", sources: [], not_measured: ["globex_*"] }))
		await flushPromises()
		first.resolve(answer())
		await flushPromises()
		expect(wrapper.text()).toContain("globex_*")
		expect(wrapper.text()).not.toContain("wazuh-lab_*")
	})

	it("stays loading when the stale request is the one to finish first", async () => {
		const first = pending()
		const second = pending()
		whatTalonSees.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise)
		const wrapper = await render()
		await wrapper.setProps({ customerCode: "GLOBEX" })
		first.resolve(answer())
		await flushPromises()
		expect(wrapper.text()).not.toContain("wazuh-lab_*")
		expect(byId(wrapper, "knowledge-sees-loading").exists()).toBe(true)
	})

	it("doesn't show a failure of the request it aborted", async () => {
		const first = pending()
		const second = pending()
		whatTalonSees.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise)
		const wrapper = await render()
		await wrapper.setProps({ customerCode: "GLOBEX" })
		first.reject(new CanceledError())
		await flushPromises()
		expect(byId(wrapper, "knowledge-sees-failure").exists()).toBe(false)
		second.resolve(answer({ customer_code: "GLOBEX" }))
		await flushPromises()
		expect(byId(wrapper, "knowledge-sees-measured").exists()).toBe(true)
	})

	it("clears a failure", async () => {
		whatTalonSees.mockRejectedValueOnce(refusal(502, { detail: "broken", code: "unavailable" }))
		const wrapper = await render()
		await wrapper.setProps({ customerCode: "GLOBEX" })
		await flushPromises()
		expect(byId(wrapper, "knowledge-sees-failure").exists()).toBe(false)
		expect(byId(wrapper, "knowledge-sees-measured").exists()).toBe(true)
	})

	it("clears the quiet line", async () => {
		whatTalonSees.mockRejectedValueOnce(refusal(404, { detail: "Not Found" }))
		const wrapper = await render()
		await wrapper.setProps({ customerCode: "GLOBEX" })
		await flushPromises()
		expect(byId(wrapper, "knowledge-sees-unsupported").exists()).toBe(false)
		expect(byId(wrapper, "knowledge-sees-measured").exists()).toBe(true)
	})
})

describe("unmounting", () => {
	it("aborts the request", async () => {
		whatTalonSees.mockReturnValue(pending().promise)
		const wrapper = await render()
		expect(signalOf(0).aborted).toBe(false)
		wrapper.unmount()
		expect(signalOf(0).aborted).toBe(true)
	})
})
