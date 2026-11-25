import type { VueWrapper } from "@vue/test-utils"
import type { StatsCustomer, StatsPreview, StatsStatus } from "@/types/sysmon-config"
import { flushPromises, mount } from "@vue/test-utils"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import SysmonConfig from "../agents/SysmonConfig.vue"

const sysmonConfig = vi.hoisted(() => ({
	getAll: vi.fn(),
	getDefaultConfig: vi.fn(),
	getConfigContent: vi.fn(),
	uploadConfigFile: vi.fn(),
	deployConfig: vi.fn(),
	saveDefaultConfig: vi.fn(),
	getDefaultSyncStatus: vi.fn(),
	syncDefaultConfig: vi.fn(),
	getStatsStatus: vi.fn(),
	setStatsSharing: vi.fn(),
	previewStats: vi.fn(),
	sendStatsNow: vi.fn()
}))
const customers = vi.hoisted(() => ({ getCustomers: vi.fn() }))
const message = vi.hoisted(() => ({ info: vi.fn(), warning: vi.fn(), error: vi.fn(), success: vi.fn() }))
const dialog = vi.hoisted(() => ({ warning: vi.fn() }))
const auth = vi.hoisted(() => ({ isAdmin: true }))

vi.mock("@/api", () => ({ default: { sysmonConfig, customers } }))
vi.mock("@/stores/auth", () => ({ useAuthStore: () => auth }))
vi.mock("@/stores/settings", () => ({ useSettingsStore: () => ({ dateFormat: { datetime: "YYYY-MM-DD HH:mm" } }) }))
vi.mock("@/composables/useNavigation", () => ({
	useNavigation: () => ({ routeCustomer: () => ({ navigate: () => {} }) })
}))
vi.mock("naive-ui", async importOriginal => ({
	...(await importOriginal<typeof import("naive-ui")>()),
	useMessage: () => message,
	useDialog: () => dialog,
	// The modals render in place, so their content can be read
	NModal: defineComponent({
		props: { show: { type: Boolean, default: false } },
		setup: (props, { slots }) => () => (props.show ? h("div", { "data-testid": "modal" }, slots.default?.()) : null)
	})
}))
vi.mock("@/components/common/Icon.vue", () => ({ default: defineComponent({ setup: () => () => h("i") }) }))
vi.mock("@/components/common/SegmentedPage.vue", () => ({
	default: defineComponent({
		setup:
			(_, { slots }) =>
			() =>
				h("div", [slots["sidebar-content"]?.(), slots["main-toolbar"]?.(), slots["main-content"]?.()])
	})
}))
vi.mock("@/components/common/XMLEditor.vue", () => ({
	default: defineComponent({
		props: { modelValue: { type: String, default: "" } },
		setup: (props, { expose }) => {
			expose({ canUndo: () => false, canRedo: () => false, undo: () => {}, redo: () => {} })
			return () => h("pre", { "data-testid": "editor" }, props.modelValue)
		}
	})
}))

const PSEUDONYM = `cust_${"a1".repeat(16)}`

function customer(overrides: Partial<StatsCustomer> = {}): StatsCustomer {
	return {
		customer_code: "contoso",
		customer_name: "Contoso Ltd",
		pseudonym: PSEUDONYM,
		sharing: true,
		install_dir_name: null,
		own_domains: [],
		withdraw: { queued: false, requested_at: null, withdrawn_at: null, last_status: null },
		due_at: "2026-11-23T14:12:00Z",
		target_week_state: null,
		last_sent_week: null,
		last_sent_state: null,
		...overrides
	}
}

function status(overrides: Partial<StatsStatus> = {}): StatsStatus {
	return {
		mode: "on",
		mode_setting: null,
		service_url: "https://sysmon-sync.socfortress.co",
		service: { accepting: true, checked_at: null, last_status: 401, not_before: null },
		last_tick: null,
		latch: null,
		target_week: "2026-W47",
		max_rule_level: 5,
		min_endpoints: 3,
		customers: [customer()],
		read_error: null,
		...overrides
	}
}

const SENT = {
	status: "terminal" as const,
	outcome: "sent" as const,
	message: "Stored by SOCFortress.",
	attempts: 1,
	last_attempt_at: "2026-11-24T06:12:00Z",
	not_before: null,
	http_status: 200,
	reason: null,
	sent_at: "2026-11-24T06:12:00Z",
	payload_sha256: "f".repeat(64),
	payload_bytes: 2400,
	patterns: 41,
	truncated: false,
	endpoints: 38,
	config: 56,
	accepted: 41,
	rejected: 0,
	rejected_by_reason: {},
	replaced: false,
	local_drops: {}
}

const STARTED = {
	outcome: "started" as const,
	message: "Sending the due reports in the background; the status shows the result when it is done.",
	week: null,
	customers: []
}

function tick(outcome: NonNullable<StatsStatus["last_tick"]>["outcome"], text: string, sent: number) {
	return {
		started_at: "2026-11-24T06:00:00Z",
		finished_at: "2026-11-24T06:01:00Z",
		outcome,
		message: text,
		sent,
		pending: 0,
		terminal: 0,
		week: "2026-W47"
	}
}

async function open(current: StatsStatus | null) {
	sysmonConfig.getStatsStatus.mockResolvedValue({ data: { success: true, message: "", status: current } })
	const wrapper = mount(SysmonConfig)
	await flushPromises()
	return wrapper
}

async function openCustomer(current: StatsStatus) {
	sysmonConfig.getAll.mockResolvedValue({ data: { success: true, customer_codes: ["contoso"] } })
	sysmonConfig.getConfigContent.mockResolvedValue({
		data: { success: true, customer_code: "contoso", config_content: "<Sysmon/>" }
	})
	const wrapper = await open(current)
	await wrapper.get(".font-mono").element.parentElement?.dispatchEvent(new Event("click"))
	await flushPromises()
	return wrapper
}

describe("the noise statistics on the Sysmon Config page", () => {
	beforeEach(() => {
		vi.clearAllMocks()
		auth.isAdmin = true
		sysmonConfig.getAll.mockResolvedValue({ data: { success: true, customer_codes: [] } })
		sysmonConfig.getDefaultSyncStatus.mockResolvedValue({ data: { success: false } })
		customers.getCustomers.mockResolvedValue({ data: { success: true, customers: [] } })
	})

	it("says when sharing is off", async () => {
		const wrapper = await open(status({ mode: "off" }))
		expect(wrapper.get("[data-testid=stats-line]").text()).toBe("Noise statistics: off (SYSMON_STATS_SHARING=off)")
		expect(wrapper.get("[data-testid=stats-send-now]").attributes("disabled")).toBeDefined()
	})

	it("says when SOCFortress is not accepting reports yet", async () => {
		const wrapper = await open(status({ service: { accepting: false, checked_at: null, last_status: 404, not_before: null } }))
		expect(wrapper.get("[data-testid=stats-line]").text()).toBe("SOCFortress is not accepting noise reports yet")
	})

	it("counts the customers the target week was sent for", async () => {
		const wrapper = await open(
			status({
				customers: [
					customer({ target_week_state: SENT }),
					customer({ customer_code: "northwind", customer_name: "Northwind" }),
					customer({ customer_code: "tailspin", sharing: false })
				]
			})
		)
		expect(wrapper.get("[data-testid=stats-line]").text()).toBe("Noise statistics 2026-W47: sent for 1 of 2 customers")
	})

	it("offers Resume when reports are paused, behind a confirmation", async () => {
		const wrapper = await open(status({ latch: { set_at: "2026-11-24T06:00:00Z", reason: "identity-leak", copilot_version: "1.0" } }))
		expect(wrapper.get("[data-testid=stats-line]").text()).toBe(
			"Paused: SOCFortress refused a report (identity-leak). Update CoPilot, or Resume"
		)
		await wrapper.get("[data-testid=stats-resume]").trigger("click")
		expect(sysmonConfig.sendStatsNow).not.toHaveBeenCalled()
		const [[options]] = dialog.warning.mock.calls
		expect(options.content).toContain("identity-leak")
		sysmonConfig.sendStatsNow.mockResolvedValue({
			data: { success: true, message: "", result: STARTED, status: status({ running: true }) }
		})
		vi.useFakeTimers()
		try {
			options.onPositiveClick()
			await flushPromises()
			expect(sysmonConfig.sendStatsNow).toHaveBeenCalledWith({ resume: true })
			expect(message.info).toHaveBeenCalledWith(STARTED.message, expect.anything())
			sysmonConfig.getStatsStatus.mockResolvedValue({
				data: { success: true, message: "", status: status({ running: false, last_tick: tick("completed", "2026-W47: 1 report(s) sent", 1) }) }
			})
			await vi.advanceTimersByTimeAsync(5000)
			await flushPromises()
			expect(message.success).toHaveBeenCalledWith("2026-W47: 1 report(s) sent", expect.anything())
		} finally {
			vi.useRealTimers()
		}
	})

	it("sends now after a confirmation, in the background, and says how it ended", async () => {
		const wrapper = await open(status({ last_tick: tick("completed", "an older run", 0) }))
		await wrapper.get("[data-testid=stats-send-now]").trigger("click")
		const [[options]] = dialog.warning.mock.calls
		sysmonConfig.sendStatsNow.mockResolvedValue({
			data: { success: true, message: "", result: STARTED, status: status({ running: true, last_tick: tick("completed", "an older run", 0) }) }
		})
		vi.useFakeTimers()
		try {
			options.onPositiveClick()
			await flushPromises()
			expect(sysmonConfig.sendStatsNow).toHaveBeenCalledWith({ resume: false })
			expect(message.info).toHaveBeenCalledWith(STARTED.message, expect.anything())
			// Still running: the button stays busy and the status is asked again
			expect(wrapper.get("[data-testid=stats-send-now]").classes().join(" ")).toContain("loading")
			sysmonConfig.getStatsStatus.mockClear()
			sysmonConfig.getStatsStatus.mockResolvedValue({
				data: { success: true, message: "", status: status({ running: true, last_tick: tick("completed", "an older run", 0) }) }
			})
			await vi.advanceTimersByTimeAsync(5000)
			expect(sysmonConfig.getStatsStatus).toHaveBeenCalledTimes(1)
			expect(message.warning).not.toHaveBeenCalled()
			const done = { ...tick("nothing_due", "No customer's 2026-W47 report is due.", 0), started_at: "2026-11-25T00:30:00Z" }
			sysmonConfig.getStatsStatus.mockResolvedValue({ data: { success: true, message: "", status: status({ running: false, last_tick: done }) } })
			await vi.advanceTimersByTimeAsync(5000)
			await flushPromises()
			expect(message.warning).toHaveBeenCalledWith("No customer's 2026-W47 report is due.", expect.anything())
			expect(wrapper.get("[data-testid=stats-send-now]").classes().join(" ")).not.toContain("loading")
			// Done: no more polling
			sysmonConfig.getStatsStatus.mockClear()
			await vi.advanceTimersByTimeAsync(20000)
			expect(sysmonConfig.getStatsStatus).not.toHaveBeenCalled()
		} finally {
			vi.useRealTimers()
		}
	})

	it("says at once when Send now cannot start", async () => {
		const wrapper = await open(status())
		await wrapper.get("[data-testid=stats-send-now]").trigger("click")
		const [[options]] = dialog.warning.mock.calls
		const off = { outcome: "sharing_off", message: "Noise statistics are off on this CoPilot (SYSMON_STATS_SHARING). Nothing was sent.", week: null, customers: [] }
		sysmonConfig.sendStatsNow.mockResolvedValue({ data: { success: true, message: "", result: off, status: status() } })
		options.onPositiveClick()
		await flushPromises()
		expect(message.warning).toHaveBeenCalledWith(off.message, expect.anything())
		expect(message.info).not.toHaveBeenCalled()
	})

	it("shows nothing to a non-admin", async () => {
		auth.isAdmin = false
		const wrapper = await open(status())
		expect(sysmonConfig.getStatsStatus).not.toHaveBeenCalled()
		expect(wrapper.find("[data-testid=stats-sharing]").exists()).toBe(false)
	})

	it("turns a customer off after a confirmation and says what was withdrawn", async () => {
		const wrapper = await openCustomer(status({ customers: [customer({ last_sent_week: "2026-W46", last_sent_state: SENT })] }))
		const strip = wrapper.get("[data-testid=stats-customer]")
		expect(strip.text()).toContain(PSEUDONYM)
		expect(wrapper.get("[data-testid=stats-customer-last]").text()).toMatch(/^W46 sent .* · 41 patterns, 41 accepted$/)

		await (wrapper.getComponent("[data-testid=stats-customer-switch]") as VueWrapper).vm.$emit("update:value", false)
		expect(sysmonConfig.setStatsSharing).not.toHaveBeenCalled()
		const [[options]] = dialog.warning.mock.calls
		expect(options.content).toBe(
			"Stop sharing noise statistics for contoso (Contoso Ltd)? CoPilot stops its weekly report and asks SOCFortress to delete the reports already sent."
		)
		sysmonConfig.setStatsSharing.mockResolvedValue({
			data: { success: true, message: "", customer: customer({ sharing: false }), withdraw: { outcome: "withdrawn", reports_deleted: 2, message: null } }
		})
		options.onPositiveClick()
		await flushPromises()
		expect(sysmonConfig.setStatsSharing).toHaveBeenCalledWith("contoso", { sharing: false })
		expect(message.success.mock.calls[0][0]).toContain("deleted 2 report(s)")
	})

	it("previews the exact payload and says nothing was sent", async () => {
		const preview: StatsPreview = {
			week: "2026-W47",
			customer_pseudonym: PSEUDONYM,
			would_send: { ok: true, why: null },
			payload: { format: "socfortress-sysmon-report/1", customer: PSEUDONYM, patterns: [{ event_id: 22, fields: { QueryName: "<b>t.fabrikam-example.com</b>" } }] },
			payload_sha256: "e".repeat(64),
			payload_bytes: 321,
			local: { raw_patterns: 3, sent: 1, dropped_by_reason: { "dns-private-suffix": 2 }, merged: 0, truncated: true, unavailable_events: [11] },
			outcome: null,
			message: null,
			ms: 40
		}
		sysmonConfig.previewStats.mockResolvedValue({ data: { success: true, message: "Nothing was sent.", preview } })
		const wrapper = await openCustomer(status())
		await wrapper.get("[data-testid=stats-customer-preview]").trigger("click")
		await flushPromises()
		expect(sysmonConfig.previewStats).toHaveBeenCalledWith("contoso")
		expect(wrapper.get("[data-testid=stats-preview-nothing-sent]").text()).toContain("Nothing was sent")
		expect(wrapper.get("[data-testid=stats-preview-sha256]").text()).toBe("e".repeat(64))
		expect(wrapper.get("[data-testid=stats-preview-drops]").text()).toContain("dns-private-suffix: 2")
		// An event left out because the indexer cannot aggregate its fields is said, never silent
		expect(wrapper.get("[data-testid=stats-preview-unavailable]").text()).toContain("event 11")
		const payload = wrapper.get("[data-testid=stats-preview-payload]")
		// Shown as text, never markup
		expect(payload.text()).toContain('"QueryName": "<b>t.fabrikam-example.com</b>"')
		expect(payload.find("b").exists()).toBe(false)
	})
})
