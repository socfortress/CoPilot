import type { VueWrapper } from "@vue/test-utils"
import type { VNodeChild } from "vue"
/**
 * The Ops tab (`TalonOps.vue` and its sections) against a mocked API: the findings table (open by
 * default, filters, cursor paging, every value as text), the detail drawer (the evidence as a list or
 * JSON, the artifact copyable, `why` and `recommendation` as plain text, never HTML), the actions with
 * the finding's stored customer, the mute window and its presets, the stale marker, the jobs panel
 * (collapsed under a summary line, schedules in words, per-customer last runs, run now for an admin
 * only, polling its runs afterwards), and the states: Ops jobs off in Talon, Talon v2 off, an old
 * Talon, a role without access. OP-2: the summary strip and its chips (severity, stale, customers),
 * the order toggle, grouping by customer, bulk acknowledge and mute (eligibility, the cap, partial
 * failures, one refresh at the end) and the links out (from finding fields and evidence ids only).
 */
import { enableAutoUnmount, flushPromises, mount, RouterLinkStub } from "@vue/test-utils"
import { AxiosError, AxiosHeaders } from "axios"
import { NRadioGroup, NSelect, NSwitch } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import { resetCustomerOptions } from "@/composables/useCustomerOptions"
import { useAuthStore } from "@/stores/auth"
import { AuthUserRole } from "@/types/auth"
import { OLD_TALON_OPS_TEXT, OPS_OFF_TITLE, QUIET_POLLS, RUN_POLL_MS, RUN_WATCH_MS, SEVERITY_ORDER_UNAVAILABLE, V2_OFF_TEXT } from "../ops"
import TalonOps from "../TalonOps.vue"

const api = {
	listFindings: vi.fn(),
	summary: vi.fn(),
	getFinding: vi.fn(),
	acknowledge: vi.fn(),
	mute: vi.fn(),
	reopen: vi.fn(),
	listJobs: vi.fn(),
	listRuns: vi.fn(),
	runNow: vi.fn()
}
const getCustomers = vi.fn()

vi.mock("@/api", () => ({
	default: {
		talonOps: new Proxy(
			{},
			{
				get:
					(_target, name: string) =>
					(...args: unknown[]) =>
						api[name as keyof typeof api](...args)
			}
		),
		customers: { getCustomers: (...args: unknown[]) => getCustomers(...args) }
	}
}))

const T = "2026-10-24T06:00:00Z"
const XSS = `<img src=x onerror="window.__pwned=1"> **bold** [link](http://evil.invalid)`

function finding(id: number, overrides: Record<string, unknown> = {}) {
	return {
		id,
		fingerprint: `quiet_endpoints:ACME:agent:${id}`,
		job: "quiet_endpoints",
		job_version: 1,
		customer_code: "ACME",
		kind: "wazuh_quiet",
		severity: "medium",
		title: `host-${id}: not seen by Wazuh for 5 days`,
		evidence: { agent_id: `00${id}`, wazuh_days_quiet: 5.1, critical_asset: false, conditions: ["wazuh_quiet"] },
		evidence_truncated: false,
		artifact: null,
		why: `Why: ${XSS}`,
		recommendation: `Do: ${XSS}\nsecond line`,
		priority: 2,
		explained: true,
		status: "open",
		first_seen: T,
		last_seen: T,
		resolved_at: null,
		resolved_reason: null,
		stale_since: null,
		muted_until: null,
		acted_by: null,
		acted_at: null,
		notified_at: null,
		updated_at: T,
		...overrides
	}
}

function opsRun(customer: string | null, overrides: Record<string, unknown> = {}) {
	return {
		id: `quiet_endpoints:${customer ?? "-"}:${T}`,
		job: "quiet_endpoints",
		job_version: 1,
		customer_code: customer,
		tick: T,
		triggered_by: "schedule",
		status: "ok",
		collected: true,
		explained: "explained",
		candidates: 2,
		new: 1,
		updated: 1,
		resolved: 0,
		error: null,
		cost_usd: "0.001",
		duration_ms: 100,
		started_at: T,
		finished_at: T,
		...overrides
	}
}

function job(name: string, overrides: Record<string, unknown> = {}) {
	return {
		name,
		title: name === "quiet_endpoints" ? "Endpoints gone quiet" : "Log sources gone silent",
		version: 1,
		scope: "customer",
		enabled: true,
		schedule: "0 6 * * *",
		schedule_status: "ACTIVE",
		last_fired_at: T,
		needs: ["copilot_db"],
		settings: {},
		last_run: {
			id: "r1",
			job: name,
			job_version: 1,
			customer_code: "ACME",
			tick: T,
			triggered_by: "schedule",
			status: "ok",
			collected: true,
			explained: "explained",
			candidates: 2,
			new: 1,
			updated: 1,
			resolved: 0,
			error: null,
			cost_usd: "0.001",
			duration_ms: 100,
			started_at: T,
			finished_at: T
		},
		last_runs: [],
		next_run: "2026-10-25T06:00:00Z",
		...overrides
	}
}

function counts(total = 0, over: Record<string, number> = {}) {
	return { total, high: 0, medium: 0, low: 0, info: 0, stale: 0, ...over }
}

function summaryOf(overrides: Record<string, unknown> = {}) {
	return {
		success: true,
		message: "",
		open: counts(7, { high: 1, medium: 2, low: 3, info: 1, stale: 2 }),
		acknowledged: 3,
		muted: 1,
		by_job: [{ job: "quiet_endpoints", ...counts(4, { high: 1, medium: 2, low: 1 }) }],
		by_customer: [
			{ customer_code: "ACME", ...counts(6, { high: 1, medium: 2, low: 2, info: 1, stale: 2 }) },
			{ customer_code: null, ...counts(1, { low: 1 }) }
		],
		dropped: 0,
		withheld: false,
		...overrides
	}
}

function ok<T>(data: T) {
	return Promise.resolve({ data })
}

/** The table's one page: these findings. */
function rows(...items: ReturnType<typeof finding>[]) {
	api.listFindings.mockImplementation(() => ok({ success: true, message: "", items, next_cursor: null, dropped: 0 }))
}

function refusal(status: number, data: unknown) {
	const headers = new AxiosHeaders()
	return Promise.reject(
		new AxiosError("x", "ERR", undefined, undefined, { status, statusText: "", data, headers, config: { headers } })
	)
}

// ── stubs: naive's drawer without teleports, the table as plain rows, the date picker as an input ──

const Drawer = defineComponent({
	props: { show: { type: Boolean, default: false } },
	setup:
		(props, { slots }) =>
		() =>
			props.show ? h("div", { "data-testid": "drawer-stub" }, slots.default?.()) : null
})
const Passthrough = defineComponent({
	setup:
		(_, { slots }) =>
		() =>
			h("div", slots.default?.())
})
interface Column {
	key: string
	render?: (row: Record<string, unknown>, index: number) => VNodeChild
}
const DataTable = defineComponent({
	props: {
		columns: { type: Array, default: () => [] },
		data: { type: Array, default: () => [] },
		rowProps: { type: Function, default: null }
	},
	setup:
		(props, { slots }) =>
		() =>
			props.data.length
				? h(
						"table",
						(props.data as Record<string, unknown>[]).map((row, i) =>
							h(
								"tr",
								props.rowProps ? props.rowProps(row) : {},
								(props.columns as Column[]).map(col =>
									h("td", { "data-col": col.key }, [
										(col.render ? col.render(row, i) : String(row[col.key])) as never
									])
								)
							)
						)
					)
				: h("div", slots.empty?.())
})
// naive's tooltip shows its content on hover only: here both the trigger and the content render.
const Tooltip = defineComponent({
	setup:
		(_, { slots }) =>
		() =>
			h("span", [slots.trigger?.(), h("span", { "data-testid": "tooltip-content" }, slots.default?.())])
})
const DatePicker = defineComponent({
	props: { value: { type: Number, default: null }, size: { type: String, default: "" } },
	emits: ["update:value"],
	setup:
		(props, { emit }) =>
		() =>
			h("input", {
				"data-testid": "date-picker",
				value: props.value ?? "",
				onInput: (e: Event) => emit("update:value", Number((e.target as HTMLInputElement).value))
			})
})

function render(props: Record<string, unknown> = {}) {
	return mount(TalonOps, {
		props,
		global: {
			stubs: {
				Drawer,
				DrawerContent: Passthrough,
				DataTable,
				DatePicker,
				Tooltip,
				Icon: true,
				RouterLink: RouterLinkStub
			}
		}
	})
}

type Wrapper = ReturnType<typeof render>

function signInAs(role: AuthUserRole) {
	useAuthStore().user = { access_token: "t", username: "ana", email: "", role }
}

async function settle() {
	await flushPromises()
	await flushPromises()
}

function byId(wrapper: Wrapper, id: string) {
	return wrapper.find(`[data-testid="${id}"]`)
}

function selectWith(wrapper: Wrapper, testId: string) {
	const select = wrapper.findAllComponents(NSelect).find(s => s.attributes("data-testid") === testId)
	if (!select) throw new Error(`no select ${testId}`)
	return select
}

function switchWith(wrapper: Wrapper, testId: string) {
	const control = wrapper.findAllComponents(NSwitch).find(s => s.attributes("data-testid") === testId)
	if (!control) throw new Error(`no switch ${testId}`)
	return control
}

enableAutoUnmount(afterEach)

beforeEach(() => {
	setActivePinia(createPinia())
	resetCustomerOptions()
	for (const fn of Object.values(api)) fn.mockReset()
	getCustomers.mockReset()
	getCustomers.mockReturnValue(ok({ customers: [{ customer_code: "ACME", customer_name: "Acme" }] }))
	api.listJobs.mockImplementation(() =>
		ok({
			success: true,
			message: "",
			any_enabled: true,
			items: [job("quiet_endpoints"), job("silent_log_sources")]
		})
	)
	api.listFindings.mockImplementation(() =>
		ok({
			success: true,
			message: "",
			items: [finding(1), finding(2, { severity: "high" })],
			next_cursor: "100.2",
			dropped: 0
		})
	)
	api.summary.mockImplementation(() => ok(summaryOf()))
	api.getFinding.mockImplementation((id: number) => ok({ success: true, message: "", finding: finding(id) }))
	api.acknowledge.mockImplementation((id: number) =>
		ok({ success: true, message: "", finding: finding(id, { status: "acknowledged", acted_by: "ana" }) })
	)
	api.reopen.mockImplementation((id: number) => ok({ success: true, message: "", finding: finding(id) }))
	api.mute.mockImplementation((id: number, until: string) =>
		ok({ success: true, message: "", finding: finding(id, { status: "muted", muted_until: until }) })
	)
	api.listRuns.mockImplementation(() => ok({ success: true, message: "", items: [opsRun("ACME")], dropped: 0 }))
	api.runNow.mockImplementation(() =>
		ok({ success: true, message: "", job: "quiet_endpoints", workflow_id: "w", status: "queued" })
	)
	delete (window as unknown as { __pwned?: number }).__pwned
})

describe("the findings table", () => {
	it("lists open findings by default, with every column as text", async () => {
		signInAs(AuthUserRole.Analyst)
		const wrapper = render()
		await settle()
		expect(api.listFindings).toHaveBeenCalledTimes(1)
		expect(api.listFindings.mock.calls[0][0]).toMatchObject({ status: "open", cursor: null, platform: false })
		const row = byId(wrapper, "talon-ops-row-1")
		expect(row.find('[data-col="title"]').text()).toBe("host-1: not seen by Wazuh for 5 days")
		expect(row.find('[data-col="customer_code"]').text()).toBe("ACME")
		expect(row.find('[data-col="job"]').text()).toBe("Endpoints gone quiet")
		expect(row.find('[data-col="severity"]').text()).toBe("Medium")
		expect(row.find('[data-col="status"]').text()).toContain("Open")
		expect(byId(wrapper, "talon-ops-row-2").find('[data-col="severity"]').text()).toBe("High")
	})

	it("filters by job, customer, status and severity, starting again from the first page", async () => {
		signInAs(AuthUserRole.Analyst)
		const wrapper = render()
		await settle()
		selectWith(wrapper, "talon-ops-filter-severity").vm.$emit("update:value", "high")
		await settle()
		selectWith(wrapper, "talon-ops-filter-job").vm.$emit("update:value", "silent_log_sources")
		await settle()
		selectWith(wrapper, "talon-ops-filter-customer").vm.$emit("update:value", "ACME")
		await settle()
		selectWith(wrapper, "talon-ops-filter-status").vm.$emit("update:value", null)
		await settle()
		expect(api.listFindings.mock.calls.at(-1)?.[0]).toMatchObject({
			job: "silent_log_sources",
			customer_code: "ACME",
			status: null,
			severity: "high",
			cursor: null
		})
	})

	it("offers platform findings to an admin only", async () => {
		signInAs(AuthUserRole.Analyst)
		const analyst = render()
		await settle()
		expect(byId(analyst, "talon-ops-filter-platform").exists()).toBe(false)
		analyst.unmount()

		signInAs(AuthUserRole.Admin)
		const admin = render()
		await settle()
		switchWith(admin, "talon-ops-filter-platform").vm.$emit("update:value", true)
		await settle()
		expect(api.listFindings.mock.calls.at(-1)?.[0]).toMatchObject({ platform: true, customer_code: null })
	})

	it("pages with the cursor", async () => {
		signInAs(AuthUserRole.Analyst)
		const wrapper = render()
		await settle()
		api.listFindings.mockImplementationOnce(() =>
			ok({ success: true, message: "", items: [finding(3)], next_cursor: null, dropped: 0 })
		)
		await byId(wrapper, "talon-ops-more").trigger("click")
		await settle()
		expect(api.listFindings.mock.calls.at(-1)?.[0]).toMatchObject({ cursor: "100.2" })
		expect(byId(wrapper, "talon-ops-row-3").exists()).toBe(true)
		expect(byId(wrapper, "talon-ops-more").exists()).toBe(false)
	})

	it("marks a finding its job couldn't measure", async () => {
		signInAs(AuthUserRole.Analyst)
		api.listFindings.mockImplementation(() =>
			ok({
				success: true,
				message: "",
				items: [finding(1), finding(2, { stale_since: "2026-10-23T06:00:00Z" })],
				next_cursor: null,
				dropped: 0
			})
		)
		const wrapper = render()
		await settle()
		expect(byId(wrapper, "talon-ops-stale-1").exists()).toBe(false)
		const status = byId(wrapper, "talon-ops-row-2").find('[data-col="status"]')
		expect(status.text()).toContain("Open")
		const stale = byId(wrapper, "talon-ops-stale-2")
		expect(stale.text()).toMatch(/^Not measured since \w{3} \d{1,2}, \d{2}:\d{2}$/)
		const tooltip = status.find('[data-testid="tooltip-content"]').text()
		expect(tooltip).toContain("couldn't check this finding")
		expect(tooltip).toContain("can't clear")
		// Reachable by keyboard, and described for a screen reader by the same text.
		expect(stale.attributes("tabindex")).toBe("0")
		const help = byId(wrapper, "talon-ops-stale-help")
		expect(stale.attributes("aria-describedby")).toBe(help.attributes("id"))
		expect(help.text()).toBe(tooltip)
		expect(help.classes()).toContain("sr-only")
	})

	it("shows no stale marker on a resolved finding", async () => {
		signInAs(AuthUserRole.Analyst)
		api.listFindings.mockImplementation(() =>
			ok({
				success: true,
				message: "",
				items: [finding(3, { status: "resolved", stale_since: "2026-10-23T06:00:00Z" })],
				next_cursor: null,
				dropped: 0
			})
		)
		const wrapper = render()
		await settle()
		expect(byId(wrapper, "talon-ops-row-3").find('[data-col="status"]').text()).toContain("Resolved")
		expect(byId(wrapper, "talon-ops-stale-3").exists()).toBe(false)
	})

	it("says so when there are no open findings", async () => {
		signInAs(AuthUserRole.Analyst)
		api.listFindings.mockImplementation(() =>
			ok({ success: true, message: "", items: [], next_cursor: null, dropped: 0 })
		)
		const wrapper = render()
		await settle()
		expect(byId(wrapper, "talon-ops-empty").text()).toContain("No open findings")
	})
})

describe("the detail drawer", () => {
	async function opened(role = AuthUserRole.Analyst, overrides: Record<string, unknown> = {}) {
		signInAs(role)
		api.getFinding.mockImplementation((id: number) =>
			ok({ success: true, message: "", finding: finding(id, overrides) })
		)
		const wrapper = render()
		await settle()
		await byId(wrapper, "talon-ops-row-1").trigger("click")
		await settle()
		return wrapper
	}

	it("reads the finding with its stored customer and shows the model's text as plain text", async () => {
		const wrapper = await opened()
		expect(api.getFinding).toHaveBeenCalledWith(1, "ACME", expect.anything())
		const why = byId(wrapper, "talon-ops-detail-why")
		expect(why.text()).toBe(`Why: ${XSS}`)
		expect(why.find("img").exists()).toBe(false)
		expect(why.find("strong").exists()).toBe(false)
		expect(why.find("a").exists()).toBe(false)
		const recommendation = byId(wrapper, "talon-ops-detail-recommendation")
		expect(recommendation.text()).toContain("second line")
		expect(recommendation.find("img").exists()).toBe(false)
		expect(recommendation.classes()).toContain("whitespace-pre-wrap")
		expect(wrapper.html()).not.toContain('<img src="x"')
		expect((window as unknown as { __pwned?: number }).__pwned).toBeUndefined()
	})

	it("shows the evidence as its job's view, as a list, or as JSON", async () => {
		const wrapper = await opened()
		expect(byId(wrapper, "talon-ops-evidence-quiet-endpoints").exists()).toBe(true)
		expect(byId(wrapper, "talon-ops-detail-evidence").exists()).toBe(false)
		await byId(wrapper, "talon-ops-detail-evidence-view-toggle").trigger("click")
		const list = byId(wrapper, "talon-ops-detail-evidence")
		expect(list.text()).toContain("agent_id")
		expect(list.text()).toContain("wazuh_quiet")
		await byId(wrapper, "talon-ops-detail-evidence-toggle").trigger("click")
		expect(JSON.parse(byId(wrapper, "talon-ops-detail-evidence-json").text())).toMatchObject({ agent_id: "001" })
		expect(byId(wrapper, "talon-ops-detail-evidence-view-toggle").exists()).toBe(false)
		await byId(wrapper, "talon-ops-detail-evidence-toggle").trigger("click")
		expect(byId(wrapper, "talon-ops-evidence-quiet-endpoints").exists()).toBe(true)
	})

	it("falls back to the list when the evidence doesn't fit its job's view", async () => {
		const wrapper = await opened(AuthUserRole.Analyst, { evidence: { conditions: "not a list", agent_id: 7 } })
		expect(byId(wrapper, "talon-ops-detail-evidence-view").exists()).toBe(false)
		expect(byId(wrapper, "talon-ops-detail-evidence-view-toggle").exists()).toBe(false)
		expect(byId(wrapper, "talon-ops-detail-evidence").text()).toContain("not a list")
		await byId(wrapper, "talon-ops-detail-evidence-toggle").trigger("click")
		expect(byId(wrapper, "talon-ops-detail-evidence-json").exists()).toBe(true)
		expect(byId(wrapper, "talon-ops-detail-evidence-toggle").text()).toBe("Show as a list")
	})

	it.each([
		["disk_forecast", "disk_forecast", { node: 42, used_gb: "700" }],
		["agent_hygiene", "wazuh_version", { sample_agents: { agent_id: "001" } }],
		["mapping_drift", "field_limit", { mapped_fields: 900, total_fields_limit: "1000" }],
		["mapping_drift", "type_conflict", { conflicts: ["a", "b"] }],
		["storage_usage", "large_footprint", { families: [{ size_gb: 3 }] }],
		["noisy_events", "tuning_candidate", { share: "5%", estimated_gb_per_day: 1 }],
		["exclusion_candidates", "exclusion_candidate", { alerts: "40", verdicted: null }],
		["cluster_health", "cluster_status", { status: { nested: true } }],
		["silent_log_sources", "silent", { last_hour: "0" }]
	])("shows %s's malformed evidence (%s) as the list", async (job, kind, evidence) => {
		signInAs(AuthUserRole.Admin)
		const wrapper = await opened(AuthUserRole.Admin, { job, kind, evidence, customer_code: "ACME" })
		expect(byId(wrapper, "talon-ops-detail-evidence-view").exists()).toBe(false)
		expect(byId(wrapper, "talon-ops-detail-evidence").exists()).toBe(true)
	})

	it("shows an ISO time in the list as local time, the UTC time in its tooltip", async () => {
		const wrapper = await opened(AuthUserRole.Analyst, { job: "unknown_job", evidence: { seen: "2026-10-24T06:00:00+00:00" } })
		const value = byId(wrapper, "talon-ops-detail-evidence").find("dd bdi")
		expect(value.attributes("title")).toBe("2026-10-24 06:00 UTC")
		expect(value.text()).not.toContain("T06:00")
	})

	it("shows an artifact in a copyable code block", async () => {
		const writeText = vi.fn(() => Promise.resolve())
		Object.assign(navigator, { clipboard: { writeText } })
		const body = `<Image condition="is">C:\\Tools\\noisy.exe</Image>`
		const wrapper = await opened(AuthUserRole.Analyst, { artifact: { type: "sysmon_exclusion", body } })
		expect(byId(wrapper, "talon-ops-detail-artifact-body").element.tagName).toBe("PRE")
		expect(byId(wrapper, "talon-ops-detail-artifact-body").text()).toBe(body)
		await byId(wrapper, "talon-ops-detail-copy").trigger("click")
		await settle()
		expect(writeText).toHaveBeenCalledWith(body)
	})

	it("acknowledges with the stored customer and updates the row", async () => {
		const wrapper = await opened()
		await byId(wrapper, "talon-ops-acknowledge").trigger("click")
		await settle()
		expect(api.acknowledge).toHaveBeenCalledWith(1, "ACME")
		expect(byId(wrapper, "talon-ops-detail-status").text()).toContain("Acknowledged")
		expect(byId(wrapper, "talon-ops-row-1").find('[data-col="status"]').text()).toContain("Acknowledged")
		expect(byId(wrapper, "talon-ops-reopen").exists()).toBe(true)
		expect(byId(wrapper, "talon-ops-acknowledge").exists()).toBe(false)
	})

	it("mutes until a time inside the window only", async () => {
		const wrapper = await opened()
		const picker = byId(wrapper, "talon-ops-mute-until")
		await picker.setValue(String(Date.now() - 1000))
		expect(byId(wrapper, "talon-ops-mute").attributes("disabled")).toBeDefined()
		await picker.setValue(String(Date.now() + 91 * 24 * 3600 * 1000))
		expect(byId(wrapper, "talon-ops-mute").attributes("disabled")).toBeDefined()
		const until = Date.now() + 3 * 24 * 3600 * 1000
		await picker.setValue(String(until))
		await byId(wrapper, "talon-ops-mute").trigger("click")
		await settle()
		expect(api.mute).toHaveBeenCalledWith(1, new Date(until).toISOString(), "ACME")
		expect(byId(wrapper, "talon-ops-detail-status").text()).toContain("Muted")
	})

	it("offers 1, 7 and 30 day mute presets beside the picker", async () => {
		const now = Date.UTC(2026, 9, 24, 12)
		vi.useFakeTimers({ toFake: ["Date"], now })
		try {
			const wrapper = await opened()
			const picker = byId(wrapper, "talon-ops-mute-until")
			// Calendar days: the same local time of day.
			const inDays = (days: number) => {
				const at = new Date(now)
				at.setDate(at.getDate() + days)
				return at.getTime()
			}
			await byId(wrapper, "talon-ops-mute-preset-1").trigger("click")
			expect((picker.element as HTMLInputElement).value).toBe(String(inDays(1)))
			await byId(wrapper, "talon-ops-mute-preset-7").trigger("click")
			expect((picker.element as HTMLInputElement).value).toBe(String(inDays(7)))
			await byId(wrapper, "talon-ops-mute-preset-30").trigger("click")
			expect((picker.element as HTMLInputElement).value).toBe(String(inDays(30)))
			await settle()
			// A preset only sets the picker: muting is still the Mute button's.
			expect(api.mute).not.toHaveBeenCalled()
			expect(byId(wrapper, "talon-ops-mute").attributes("disabled")).toBeUndefined()
			await byId(wrapper, "talon-ops-mute").trigger("click")
			await settle()
			expect(api.mute).toHaveBeenCalledWith(1, new Date(inDays(30)).toISOString(), "ACME")
		} finally {
			vi.useRealTimers()
		}
	})

	it("reopens an acknowledged finding, and offers nothing on a resolved one", async () => {
		const wrapper = await opened(AuthUserRole.Analyst, { status: "acknowledged" })
		await byId(wrapper, "talon-ops-reopen").trigger("click")
		await settle()
		expect(api.reopen).toHaveBeenCalledWith(1, "ACME")
		wrapper.unmount()

		const resolved = await opened(AuthUserRole.Analyst, { status: "resolved" })
		expect(byId(resolved, "talon-ops-acknowledge").exists()).toBe(false)
		expect(byId(resolved, "talon-ops-reopen").exists()).toBe(false)
		expect(byId(resolved, "talon-ops-mute").exists()).toBe(false)
		expect(byId(resolved, "talon-ops-resolved-note").exists()).toBe(true)
	})

	it("shows a refused action's fixed text", async () => {
		const wrapper = await opened()
		api.acknowledge.mockImplementation(() =>
			refusal(409, { detail: "a resolved finding can't be acknowledged", code: "conflict" })
		)
		await byId(wrapper, "talon-ops-acknowledge").trigger("click")
		await settle()
		expect(byId(wrapper, "talon-ops-action-error").text()).toBe("a resolved finding can't be acknowledged")
	})

	it("opens the finding a notification links to", async () => {
		signInAs(AuthUserRole.Analyst)
		const wrapper = render({ initialFinding: 7 })
		await settle()
		expect(api.getFinding).toHaveBeenCalledWith(7, null, expect.anything())
		expect(byId(wrapper, "talon-ops-detail-title").text()).toBe("host-7: not seen by Wazuh for 5 days")
	})
})

describe("the jobs panel", () => {
	function jobsWith(items: ReturnType<typeof job>[]) {
		api.listJobs.mockImplementation(() => ok({ success: true, message: "", any_enabled: true, items }))
	}

	it("is collapsed by default under a summary line, and expands", async () => {
		signInAs(AuthUserRole.Analyst)
		const wrapper = render()
		await settle()
		const summary = byId(wrapper, "talon-ops-jobs-summary")
		expect(summary.text()).toBe("2 enabled · last runs ok")
		expect(summary.attributes("data-tone")).toBe("ok")
		const toggle = byId(wrapper, "talon-ops-jobs-toggle")
		expect(toggle.attributes("aria-expanded")).toBe("false")
		// v-show: the table is in the page, hidden (`isVisible` needs a mounted document).
		const table = () => (byId(wrapper, "talon-ops-jobs-table").element as HTMLElement).style.display
		expect(table()).toBe("none")
		await toggle.trigger("click")
		expect(toggle.attributes("aria-expanded")).toBe("true")
		expect(table()).toBe("")
		expect(byId(wrapper, "talon-ops-jobs-summary").text()).toBe("2 enabled · last runs ok")
	})

	it("summary: amber naming the partial and skipped jobs", async () => {
		signInAs(AuthUserRole.Analyst)
		jobsWith([
			job("quiet_endpoints"),
			job("mapping_drift", { last_runs: [opsRun("ACME"), opsRun("BETA", { status: "partial" })] }),
			job("disk_forecast", { last_run: opsRun(null, { status: "skipped" }), last_runs: [] })
		])
		const wrapper = render()
		await settle()
		const summary = byId(wrapper, "talon-ops-jobs-summary")
		expect(summary.text()).toBe("1 partial (mapping_drift) · 1 skipped (disk_forecast)")
		expect(summary.attributes("data-tone")).toBe("warning")
		expect(summary.classes()).toContain("text-warning")
	})

	it("summary: red with a failed run", async () => {
		signInAs(AuthUserRole.Analyst)
		jobsWith([
			job("quiet_endpoints"),
			job("cluster_health", { last_runs: [opsRun(null, { status: "failed", error: "the indexer is down" })] })
		])
		const wrapper = render()
		await settle()
		const summary = byId(wrapper, "talon-ops-jobs-summary")
		expect(summary.text()).toBe("1 failed (cluster_health)")
		expect(summary.attributes("data-tone")).toBe("error")
		expect(summary.classes()).toContain("text-error")
		expect(byId(wrapper, "talon-ops-job-status-cluster_health").classes()).toContain("text-error")
	})

	it("shows each job's schedule in words (the cron in a tooltip), last and next run", async () => {
		signInAs(AuthUserRole.Analyst)
		jobsWith([job("quiet_endpoints"), job("silent_log_sources", { schedule: "*/10 * * * *" })])
		const wrapper = render()
		await settle()
		const quiet = byId(wrapper, "talon-ops-job-quiet_endpoints")
		expect(quiet.text()).toContain("Endpoints gone quiet")
		expect(byId(wrapper, "talon-ops-job-schedule-quiet_endpoints").text()).toBe("Daily 06:00 UTC")
		expect(byId(wrapper, "talon-ops-job-cron-quiet_endpoints").text()).toContain("0 6 * * *")
		expect(byId(wrapper, "talon-ops-job-schedule-silent_log_sources").text()).toBe("*/10 * * * *")
		expect(quiet.find('[data-testid="talon-ops-job-last-run"]').text()).toContain("ok")
		expect(quiet.find('[data-testid="talon-ops-job-next-run"]').text()).not.toBe("—")
		await byId(wrapper, "talon-ops-job-runs-toggle-quiet_endpoints").trigger("click")
		expect(byId(wrapper, "talon-ops-job-runs-quiet_endpoints").text()).toContain("1 new, 1 updated, 0 resolved")
	})

	it("lists the newest run per customer, the worst status first", async () => {
		signInAs(AuthUserRole.Analyst)
		jobsWith([
			job("quiet_endpoints", {
				last_runs: [
					opsRun("ACME", { new: 2, updated: 0, resolved: 1 }),
					opsRun("BETA", { status: "partial", error: "the indexer timed out", new: null })
				]
			})
		])
		const wrapper = render()
		await settle()
		const toggle = byId(wrapper, "talon-ops-job-runs-toggle-quiet_endpoints")
		expect(byId(wrapper, "talon-ops-job-status-quiet_endpoints").text()).toBe("partial")
		expect(toggle.text()).toContain("2 customers")
		expect(byId(wrapper, "talon-ops-job-runs-quiet_endpoints").exists()).toBe(false)
		await toggle.trigger("click")
		expect(toggle.attributes("aria-expanded")).toBe("true")
		const lines = byId(wrapper, "talon-ops-job-runs-quiet_endpoints").findAll('[data-testid="talon-ops-job-run"]')
		expect(lines).toHaveLength(2)
		// Talon lists ACME first; the partial run comes first here.
		expect(lines[0].text()).toContain("BETA")
		expect(lines[0].text()).toContain("partial")
		expect(lines[0].text()).toContain("? new, 1 updated, 0 resolved")
		expect(lines[0].text()).toContain("the indexer timed out")
		expect(lines[1].text()).toContain("ACME")
		expect(lines[1].text()).toContain("ok")
		expect(lines[1].text()).toContain("2 new, 0 updated, 1 resolved")
		await toggle.trigger("click")
		expect(byId(wrapper, "talon-ops-job-runs-quiet_endpoints").exists()).toBe(false)
	})

	it("judges a job by its newest tick: an old skipped row and a customer gone from scope don't count", async () => {
		signInAs(AuthUserRole.Analyst)
		const OLD = "2026-09-30T06:00:00+00:00"
		jobsWith([
			job("quiet_endpoints", {
				last_runs: [
					opsRun("ACME"),
					opsRun("BETA", { id: "beta" }),
					opsRun(null, { id: "old-skip", status: "skipped", tick: OLD, finished_at: OLD }),
					opsRun("GONE", { id: "gone", status: "failed", tick: OLD, finished_at: OLD })
				]
			})
		])
		const wrapper = render()
		await settle()
		expect(byId(wrapper, "talon-ops-jobs-summary").text()).toBe("1 enabled · last runs ok")
		expect(byId(wrapper, "talon-ops-job-status-quiet_endpoints").text()).toBe("ok")
		const toggle = byId(wrapper, "talon-ops-job-runs-toggle-quiet_endpoints")
		expect(toggle.text()).toContain("2 customers")
		await toggle.trigger("click")
		const lines = byId(wrapper, "talon-ops-job-runs-quiet_endpoints").findAll('[data-testid="talon-ops-job-run"]')
		expect(lines.map(l => l.text().split(" ")[0])).toEqual(["ACME", "BETA"])
	})

	it("shows a tick still in progress as running, hiding no customer's previous failure", async () => {
		const NOW = Date.parse("2026-10-24T08:00:00Z")
		vi.useFakeTimers({ toFake: ["Date"], now: NOW })
		try {
			signInAs(AuthUserRole.Analyst)
			const NOW_TICK = "2026-10-24T07:50:00+00:00"
			const YESTERDAY = "2026-10-23T07:50:00+00:00"
			const customers = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]
			jobsWith([
				job("storage_usage", {
					last_runs: customers.map((c, i) =>
						i < 4
							? opsRun(c, { id: `now-${c}`, tick: NOW_TICK, finished_at: "2026-10-24T07:55:00Z" })
							: opsRun(c, {
									id: `old-${c}`,
									tick: YESTERDAY,
									finished_at: YESTERDAY,
									status: c === "E" ? "failed" : "ok",
									error: c === "E" ? "the indexer timed out" : null
								})
					)
				})
			])
			const wrapper = render()
			await settle()
			expect(byId(wrapper, "talon-ops-jobs-summary").text()).toBe(
				"1 failed (storage_usage) · 1 running (storage_usage 4 of 10)"
			)
			expect(byId(wrapper, "talon-ops-jobs-summary").attributes("data-tone")).toBe("error")
			expect(byId(wrapper, "talon-ops-job-status-storage_usage").text()).toBe("failed")
			expect(byId(wrapper, "talon-ops-job-running-storage_usage").text()).toBe("· running (4 of 10)")
			const toggle = byId(wrapper, "talon-ops-job-runs-toggle-storage_usage")
			expect(toggle.text()).toContain("10 customers")
			await toggle.trigger("click")
			const lines = byId(wrapper, "talon-ops-job-runs-storage_usage").findAll('[data-testid="talon-ops-job-run"]')
			expect(lines).toHaveLength(10)
			expect(lines[0].text()).toContain("E")
			expect(lines[0].text()).toContain("the indexer timed out")
		} finally {
			vi.useRealTimers()
		}
	})

	it("tells a non-admin a platform job's runs are an admin's, and leaves it out of the summary", async () => {
		signInAs(AuthUserRole.Analyst)
		jobsWith([
			job("quiet_endpoints"),
			job("cluster_health", { scope: "platform", last_run: null, last_runs: [], schedule: "5 * * * *" })
		])
		const wrapper = render()
		await settle()
		expect(byId(wrapper, "talon-ops-job-platform-cluster_health").text()).toBe("Platform job (admins only)")
		expect(byId(wrapper, "talon-ops-job-cluster_health").text()).not.toContain("No run yet")
		expect(byId(wrapper, "talon-ops-jobs-summary").text()).toBe("1 enabled · last runs ok")
		expect(byId(wrapper, "talon-ops-job-schedule-cluster_health").text()).toBe("Hourly at :05 UTC")
	})

	it("offers run now to an admin only, for an enabled job", async () => {
		signInAs(AuthUserRole.Analyst)
		const analyst = render()
		await settle()
		expect(byId(analyst, "talon-ops-run-quiet_endpoints").exists()).toBe(false)
		analyst.unmount()

		signInAs(AuthUserRole.Admin)
		jobsWith([job("quiet_endpoints"), job("silent_log_sources", { enabled: false, next_run: null })])
		const admin = render()
		await settle()
		expect(byId(admin, "talon-ops-run-silent_log_sources").attributes("disabled")).toBeDefined()
		await byId(admin, "talon-ops-run-quiet_endpoints").trigger("click")
		await settle()
		expect(api.runNow).toHaveBeenCalledWith("quiet_endpoints")
		expect(byId(admin, "talon-ops-run-message").text()).toContain("queued")
	})
})

describe("run now, then its runs", () => {
	const CLICK = Date.parse("2026-10-24T08:00:00Z")
	// Talon's tick for this click (DBOS's `trigger_schedule` time), in its workflow id and its runs.
	const TICK = "2026-10-24T07:59:58.123456+00:00"
	const WORKFLOW = `sched-talon-ops:quiet_endpoints-trigger-${TICK}`
	let runs: ReturnType<typeof opsRun>[]

	beforeEach(() => {
		// Only the clocks: flushPromises still uses the real setImmediate.
		vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout", "Date"], now: CLICK })
		runs = [opsRun("ACME")]
		api.listRuns.mockImplementation(() => ok({ success: true, message: "", items: runs, dropped: 0 }))
		api.runNow.mockImplementation(() =>
			ok({ success: true, message: "", job: "quiet_endpoints", workflow_id: WORKFLOW, status: "queued" })
		)
	})

	afterEach(() => {
		vi.useRealTimers()
	})

	async function clicked(items = [job("quiet_endpoints")]) {
		signInAs(AuthUserRole.Admin)
		api.listJobs.mockImplementation(() => ok({ success: true, message: "", any_enabled: true, items }))
		const wrapper = render()
		await settle()
		await byId(wrapper, "talon-ops-run-quiet_endpoints").trigger("click")
		await settle()
		return wrapper
	}

	async function tick(ms = RUN_POLL_MS) {
		await vi.advanceTimersByTimeAsync(ms)
		await settle()
	}

	/** The polls in a row without a new run that end the watch once every run expected is in. */
	async function quietPolls() {
		for (let i = 0; i < QUIET_POLLS; i++) await tick()
	}

	const message = (wrapper: Wrapper) => byId(wrapper, "talon-ops-run-message").text()

	const fresh = (customer: string | null, overrides: Record<string, unknown> = {}) =>
		opsRun(customer, {
			id: `quiet_endpoints:${customer ?? "-"}:${TICK}`,
			tick: TICK,
			triggered_by: "manual",
			finished_at: "2026-10-24T08:00:20Z",
			new: 2,
			updated: 1,
			resolved: 3,
			...overrides
		})

	it("reloads the jobs and the findings once the run is in, and says what it found", async () => {
		const wrapper = await clicked()
		expect(api.listRuns).toHaveBeenCalledWith({ job: "quiet_endpoints", limit: 200 }, expect.anything())
		expect(message(wrapper)).toContain("queued")
		expect(byId(wrapper, "talon-ops-run-quiet_endpoints").attributes("disabled")).toBeDefined()
		const jobsCalls = api.listJobs.mock.calls.length
		const findingsCalls = api.listFindings.mock.calls.length

		await tick()
		expect(api.listRuns).toHaveBeenCalledTimes(2)
		expect(api.listJobs).toHaveBeenCalledTimes(jobsCalls)

		runs = [fresh("ACME"), ...runs]
		await tick()
		// In; a few more polls make sure no other customer's run follows.
		for (let i = 1; i < QUIET_POLLS; i++) await tick()
		expect(api.listJobs).toHaveBeenCalledTimes(jobsCalls)
		await tick()
		expect(api.listJobs).toHaveBeenCalledTimes(jobsCalls + 1)
		expect(api.listFindings).toHaveBeenCalledTimes(findingsCalls + 1)
		expect(message(wrapper)).toBe("Endpoints gone quiet finished: 2 new, 1 updated, 3 resolved.")
		expect(byId(wrapper, "talon-ops-run-quiet_endpoints").attributes("disabled")).toBeUndefined()

		const polls = api.listRuns.mock.calls.length
		await tick(RUN_WATCH_MS)
		expect(api.listRuns).toHaveBeenCalledTimes(polls)
	})

	it("ignores a scheduled run and another click's run finishing meanwhile", async () => {
		const wrapper = await clicked()
		runs = [
			opsRun("ACME", {
				id: "sched",
				tick: "2026-10-24T08:00:15+00:00",
				finished_at: "2026-10-24T08:00:16Z",
				new: 9
			}),
			opsRun("ACME", {
				id: "other",
				tick: "2026-10-24T07:58:00+00:00",
				triggered_by: "manual",
				finished_at: "2026-10-24T08:00:10Z",
				new: 7
			}),
			...runs
		]
		await tick()
		await tick()
		expect(message(wrapper)).toContain("queued")
		runs = [fresh("ACME"), ...runs]
		await tick()
		await quietPolls()
		expect(message(wrapper)).toBe("Endpoints gone quiet finished: 2 new, 1 updated, 3 resolved.")
	})

	it("waits for every customer's run, reloading once at the end", async () => {
		const wrapper = await clicked([
			job("quiet_endpoints", { last_runs: [opsRun("ACME"), opsRun("BETA", { id: "beta-old" })] })
		])
		const jobsCalls = api.listJobs.mock.calls.length
		runs = [fresh("ACME"), ...runs]
		await tick()
		expect(message(wrapper)).toBe(
			"Endpoints gone quiet: 2 new, 1 updated, 3 resolved so far (1 of 2 customers); still running."
		)
		expect(api.listJobs).toHaveBeenCalledTimes(jobsCalls)
		runs = [fresh("BETA", { status: "partial", new: 0, updated: 0, resolved: 1 }), ...runs]
		await tick()
		await quietPolls()
		expect(message(wrapper)).toBe("Endpoints gone quiet finished (partial): 2 new, 1 updated, 4 resolved.")
		expect(api.listJobs).toHaveBeenCalledTimes(jobsCalls + 1)
	})

	it("counts a customer missing from the last tick that comes in a few polls late", async () => {
		// The last tick ran for ACME and BETA; NEW was added since, and its unit is queued behind them.
		const wrapper = await clicked([
			job("quiet_endpoints", { last_runs: [opsRun("ACME"), opsRun("BETA", { id: "beta-old" })] })
		])
		runs = [fresh("ACME"), fresh("BETA"), ...runs]
		await tick()
		// Two polls go by with nothing new: more than one poll interval, fewer than the quiet polls.
		await tick()
		await tick()
		expect(message(wrapper)).toContain("queued")
		runs = [fresh("NEW", { new: 5, updated: 0, resolved: 0 }), ...runs]
		await tick()
		await quietPolls()
		expect(message(wrapper)).toBe("Endpoints gone quiet finished: 9 new, 2 updated, 6 resolved.")
	})

	it("isn't done at 4 of 10 while the last tick is still in progress", async () => {
		// The scheduled tick at 07:50 has run for 4 of its 10 customers; 6 still show yesterday's run.
		const NOW_TICK = "2026-10-24T07:50:00+00:00"
		const YESTERDAY = "2026-10-23T07:50:00+00:00"
		const customers = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]
		const lastRuns = customers.map((c, i) =>
			i < 4
				? opsRun(c, { id: `now-${c}`, tick: NOW_TICK, finished_at: "2026-10-24T07:55:00Z" })
				: opsRun(c, { id: `old-${c}`, tick: YESTERDAY, finished_at: YESTERDAY })
		)
		const wrapper = await clicked([job("quiet_endpoints", { last_runs: lastRuns })])
		const jobsCalls = api.listJobs.mock.calls.length
		runs = [...customers.slice(0, 4).map(c => fresh(c)), ...runs]
		await tick()
		await quietPolls()
		await quietPolls()
		expect(message(wrapper)).toBe(
			"Endpoints gone quiet: 8 new, 4 updated, 12 resolved so far (4 of 10 customers); still running."
		)
		expect(api.listJobs).toHaveBeenCalledTimes(jobsCalls)
		runs = [...customers.slice(4).map(c => fresh(c)), ...runs]
		await tick()
		await quietPolls()
		expect(message(wrapper)).toBe("Endpoints gone quiet finished: 20 new, 10 updated, 30 resolved.")
		expect(api.listJobs).toHaveBeenCalledTimes(jobsCalls + 1)
	})

	it("ends at a skipped run without a customer", async () => {
		const wrapper = await clicked([
			job("quiet_endpoints", { last_runs: [opsRun("ACME"), opsRun("BETA", { id: "beta-old" })] })
		])
		runs = [fresh(null, { status: "skipped", new: 0, updated: 0, resolved: 0 }), ...runs]
		await tick()
		await quietPolls()
		expect(message(wrapper)).toBe("Endpoints gone quiet finished (skipped): 0 new, 0 updated, 0 resolved.")
	})

	it("gives up after two minutes: still running, refresh later, nothing reloaded", async () => {
		const wrapper = await clicked()
		const jobsCalls = api.listJobs.mock.calls.length
		await tick(RUN_WATCH_MS - RUN_POLL_MS)
		expect(message(wrapper)).toContain("queued")
		await tick()
		expect(message(wrapper)).toBe("Endpoints gone quiet is still running; refresh later.")
		expect(api.listJobs).toHaveBeenCalledTimes(jobsCalls)
		const polls = api.listRuns.mock.calls.length
		expect(polls).toBe(1 + RUN_WATCH_MS / RUN_POLL_MS)
		await tick(RUN_WATCH_MS)
		expect(api.listRuns).toHaveBeenCalledTimes(polls)
		expect(byId(wrapper, "talon-ops-run-quiet_endpoints").attributes("disabled")).toBeUndefined()
	})

	it("at the timeout with some runs in, says so and reloads once", async () => {
		const wrapper = await clicked([
			job("quiet_endpoints", { last_runs: [opsRun("ACME"), opsRun("BETA", { id: "beta-old" })] })
		])
		const jobsCalls = api.listJobs.mock.calls.length
		runs = [fresh("ACME"), ...runs]
		await tick(RUN_WATCH_MS)
		expect(message(wrapper)).toBe(
			"Endpoints gone quiet: 2 new, 1 updated, 3 resolved so far (1 of 2 customers); the rest are still running; refresh later."
		)
		expect(api.listJobs).toHaveBeenCalledTimes(jobsCalls + 1)
	})

	it("keeps polling past a transient failure", async () => {
		const wrapper = await clicked()
		api.listRuns.mockImplementationOnce(() =>
			refusal(502, { detail: "Talon could not be reached", code: "unavailable" })
		)
		await tick()
		runs = [fresh("ACME"), ...runs]
		await tick()
		await quietPolls()
		expect(message(wrapper)).toContain("finished")
	})

	it.each([
		[403, { detail: "not one of your customers", code: "forbidden" }, "not one of your customers"],
		[404, { detail: "Not Found" }, "Talon v2 is off in CoPilot"]
	])("stops polling on a %s and says why", async (status, body, detail) => {
		const wrapper = await clicked()
		api.listRuns.mockImplementation(() => refusal(status, body))
		await tick()
		expect(message(wrapper)).toBe(`Endpoints gone quiet: its runs can't be read (${detail}).`)
		const polls = api.listRuns.mock.calls.length
		await tick(RUN_WATCH_MS)
		expect(api.listRuns).toHaveBeenCalledTimes(polls)
		expect(byId(wrapper, "talon-ops-run-quiet_endpoints").attributes("disabled")).toBeUndefined()
	})

	it("without a workflow id, matches the manual runs Talon didn't have before the click", async () => {
		api.runNow.mockImplementation(() =>
			ok({ success: true, message: "", job: "quiet_endpoints", workflow_id: null, status: "queued" })
		)
		const wrapper = await clicked()
		runs = [opsRun("ACME", { id: "sched", tick: "2026-10-24T08:00:15+00:00", new: 9 }), ...runs]
		await tick()
		await tick()
		expect(message(wrapper)).toContain("queued")
		runs = [fresh("ACME"), ...runs]
		await tick()
		await quietPolls()
		expect(message(wrapper)).toBe("Endpoints gone quiet finished: 2 new, 1 updated, 3 resolved.")
	})

	it("without a workflow id or the runs before the click, doesn't guess from the browser's clock", async () => {
		api.runNow.mockImplementation(() =>
			ok({ success: true, message: "", job: "quiet_endpoints", workflow_id: null, status: "queued" })
		)
		api.listRuns.mockImplementation(() =>
			refusal(503, { detail: "Talon could not be reached", code: "unavailable" })
		)
		signInAs(AuthUserRole.Admin)
		const wrapper = render()
		await settle()
		await byId(wrapper, "talon-ops-run-quiet_endpoints").trigger("click")
		await settle()
		// The read before queueing is tried three times, a second apart.
		await tick(1000)
		await tick(1000)
		expect(api.listRuns).toHaveBeenCalledTimes(3)
		expect(api.runNow).toHaveBeenCalledTimes(1)
		expect(message(wrapper)).toBe(
			"Endpoints gone quiet is queued to run now. Its runs can't be followed here: refresh later."
		)
		await tick(RUN_WATCH_MS)
		expect(api.listRuns).toHaveBeenCalledTimes(3)
	})

	it("stops polling when the page goes away", async () => {
		const wrapper = await clicked()
		await tick()
		const polls = api.listRuns.mock.calls.length
		wrapper.unmount()
		await tick(RUN_WATCH_MS)
		expect(api.listRuns).toHaveBeenCalledTimes(polls)
	})

	it("shows a refused run now, and polls nothing", async () => {
		api.runNow.mockImplementation(() =>
			refusal(409, { detail: "the job is not enabled (TALON_OPS_JOBS)", code: "conflict" })
		)
		const wrapper = await clicked()
		expect(message(wrapper)).toBe("the job is not enabled (TALON_OPS_JOBS)")
		const polls = api.listRuns.mock.calls.length
		await tick(RUN_WATCH_MS)
		expect(api.listRuns).toHaveBeenCalledTimes(polls)
		expect(byId(wrapper, "talon-ops-run-quiet_endpoints").attributes("disabled")).toBeUndefined()
	})
})

describe("the summary strip", () => {
	it("shows the open counts by severity, the stale count, the top customers and the acted counts", async () => {
		signInAs(AuthUserRole.Admin)
		const wrapper = render()
		await settle()
		expect(api.summary).toHaveBeenCalledTimes(1)
		expect(api.summary.mock.calls[0][0]).toEqual({ job: null, customer_code: null, platform: false })
		expect(byId(wrapper, "talon-ops-summary-severity-high").text()).toBe("High 1")
		expect(byId(wrapper, "talon-ops-summary-severity-medium").text()).toBe("Medium 2")
		expect(byId(wrapper, "talon-ops-summary-severity-low").text()).toBe("Low 3")
		expect(byId(wrapper, "talon-ops-summary-severity-info").text()).toBe("Info 1")
		expect(byId(wrapper, "talon-ops-summary-stale").text()).toBe("2 not measured")
		expect(byId(wrapper, "talon-ops-summary-customer-ACME").text()).toBe("ACME 6")
		expect(byId(wrapper, "talon-ops-summary-customer-platform").text()).toBe("Platform 1")
		expect(byId(wrapper, "talon-ops-summary-acted").text()).toBe("3 acknowledged · 1 muted")
		expect(byId(wrapper, "talon-ops-summary-withheld").exists()).toBe(false)
	})

	it("a severity chip filters the table to the open findings of that severity; again clears it", async () => {
		signInAs(AuthUserRole.Analyst)
		const wrapper = render()
		await settle()
		selectWith(wrapper, "talon-ops-filter-status").vm.$emit("update:value", "muted")
		await settle()
		await byId(wrapper, "talon-ops-summary-severity-high").trigger("click")
		await settle()
		expect(api.listFindings.mock.calls.at(-1)?.[0]).toMatchObject({
			severity: "high",
			status: "open",
			cursor: null
		})
		await byId(wrapper, "talon-ops-summary-severity-high").trigger("click")
		await settle()
		expect(api.listFindings.mock.calls.at(-1)?.[0]).toMatchObject({ severity: null, status: "open" })
	})

	it("a customer chip filters by that customer, the platform chip by platform findings", async () => {
		signInAs(AuthUserRole.Admin)
		const wrapper = render()
		await settle()
		await byId(wrapper, "talon-ops-summary-customer-ACME").trigger("click")
		await settle()
		expect(api.listFindings.mock.calls.at(-1)?.[0]).toMatchObject({ customer_code: "ACME", platform: false })
		expect(api.summary.mock.calls.at(-1)?.[0]).toEqual({ job: null, customer_code: "ACME", platform: false })
		await byId(wrapper, "talon-ops-summary-customer-platform").trigger("click")
		await settle()
		expect(api.listFindings.mock.calls.at(-1)?.[0]).toMatchObject({ customer_code: null, platform: true })
		expect(api.summary.mock.calls.at(-1)?.[0]).toEqual({ job: null, customer_code: null, platform: true })
	})

	it("the stale chip filters the loaded rows (Talon has no such filter) and says so", async () => {
		signInAs(AuthUserRole.Analyst)
		api.listFindings.mockImplementation(() =>
			ok({
				success: true,
				message: "",
				items: [finding(1), finding(2, { stale_since: T }), finding(3, { stale_since: T, status: "resolved" })],
				next_cursor: "100.3",
				dropped: 0
			})
		)
		const wrapper = render()
		await settle()
		const calls = api.listFindings.mock.calls.length
		const chip = byId(wrapper, "talon-ops-summary-stale")
		expect(chip.attributes("aria-describedby")).toBe("talon-ops-stale-filter-help")
		expect(wrapper.find("#talon-ops-stale-filter-help").text()).toContain("filters the rows already loaded")
		await chip.trigger("click")
		await settle()
		expect(api.listFindings.mock.calls.length).toBe(calls) // nothing new asked of Talon: status was open already
		expect(byId(wrapper, "talon-ops-row-1").exists()).toBe(false)
		expect(byId(wrapper, "talon-ops-row-2").exists()).toBe(true)
		expect(byId(wrapper, "talon-ops-row-3").exists()).toBe(false)
		expect(byId(wrapper, "talon-ops-stale-only").text()).toContain("1 of 3 loaded")
		expect(byId(wrapper, "talon-ops-more").exists()).toBe(true) // paging still works
		await byId(wrapper, "talon-ops-stale-only-clear").trigger("click")
		await settle()
		expect(byId(wrapper, "talon-ops-row-1").exists()).toBe(true)
	})

	it("refreshes along with the table", async () => {
		signInAs(AuthUserRole.Analyst)
		const wrapper = render()
		await settle()
		await byId(wrapper, "talon-ops-refresh").trigger("click")
		await settle()
		expect(api.listFindings).toHaveBeenCalledTimes(2)
		expect(api.summary).toHaveBeenCalledTimes(2)
	})

	it("says when counts were withheld, and leaves out what Talon's answer couldn't split", async () => {
		signInAs(AuthUserRole.Analyst)
		api.summary.mockImplementation(() =>
			ok(summaryOf({ acknowledged: null, muted: null, by_job: [], withheld: true, dropped: 1 }))
		)
		const wrapper = render()
		await settle()
		expect(byId(wrapper, "talon-ops-summary-withheld").exists()).toBe(true)
		expect(byId(wrapper, "talon-ops-summary-acted").exists()).toBe(false)
	})

	it("at Talon's row cap with counts that don't add up, says they are a lower bound", async () => {
		signInAs(AuthUserRole.Analyst)
		api.summary.mockImplementation(() =>
			ok(
				summaryOf({
					open: counts(50, { low: 50 }),
					acknowledged: null,
					muted: null,
					by_job: [],
					withheld: true,
					partial: true
				})
			)
		)
		const wrapper = render()
		await settle()
		expect(byId(wrapper, "talon-ops-summary-severity-high").text()).toBe("High ≥0")
		expect(byId(wrapper, "talon-ops-summary-severity-low").text()).toBe("Low ≥50")
		expect(byId(wrapper, "talon-ops-summary-stale").text()).toBe("≥0 not measured")
		expect(byId(wrapper, "talon-ops-summary-partial").text()).toContain("At least 50 open · top 50 customers only")
		expect(byId(wrapper, "talon-ops-summary-withheld").exists()).toBe(false)
	})

	it("a Talon without the summary: a quiet note, and the table still works", async () => {
		signInAs(AuthUserRole.Analyst)
		api.summary.mockImplementation(() => refusal(404, { detail: OLD_TALON_OPS_TEXT, code: "unsupported" }))
		const wrapper = render()
		await settle()
		expect(byId(wrapper, "talon-ops-summary-unsupported").exists()).toBe(true)
		expect(byId(wrapper, "talon-ops-row-1").exists()).toBe(true)
	})
})

describe("the order", () => {
	/** A first page in each order, with Talon's own cursors: `s<rank>.<micros>.<id>` for severity. */
	function pagedByOrder() {
		api.listFindings.mockImplementation((query: { order: string; cursor: string | null }) =>
			ok({
				success: true,
				message: "",
				items: query.cursor ? [finding(3)] : [finding(1), finding(2, { severity: "high" })],
				next_cursor: query.cursor ? null : query.order === "severity" ? "s3.1729740000000000.2" : "1729740000000000.2",
				dropped: 0
			})
		)
	}

	it("is severity by default, and the toggle asks again from the first page in the other order", async () => {
		signInAs(AuthUserRole.Analyst)
		pagedByOrder()
		const wrapper = render()
		await settle()
		expect(api.listFindings.mock.calls[0][0]).toMatchObject({ order: "severity", cursor: null })
		await byId(wrapper, "talon-ops-more").trigger("click")
		await settle()
		expect(api.listFindings.mock.calls.at(-1)?.[0]).toMatchObject({ order: "severity", cursor: "s3.1729740000000000.2" })
		wrapper.findComponent(NRadioGroup).vm.$emit("update:value", "recent")
		await settle()
		expect(api.listFindings.mock.calls.at(-1)?.[0]).toMatchObject({ order: "recent", cursor: null })
		await byId(wrapper, "talon-ops-more").trigger("click")
		await settle()
		expect(api.listFindings.mock.calls.at(-1)?.[0]).toMatchObject({ order: "recent", cursor: "1729740000000000.2" })
	})

	it("never sends the old order's cursor while the new order's first page loads", async () => {
		signInAs(AuthUserRole.Analyst)
		pagedByOrder()
		const wrapper = render()
		await settle()
		expect(byId(wrapper, "talon-ops-more").exists()).toBe(true)
		let answer: (value: unknown) => void = () => {}
		api.listFindings.mockImplementationOnce(() => new Promise(resolve => (answer = resolve)))
		wrapper.findComponent(NRadioGroup).vm.$emit("update:value", "recent")
		await settle()
		// Still loading the first page in the new order: there is no cursor to send yet.
		expect(byId(wrapper, "talon-ops-more").exists()).toBe(false)
		const calls = api.listFindings.mock.calls.length
		answer({ data: { success: true, message: "", items: [finding(1)], next_cursor: "1729740000000000.1", dropped: 0 } })
		await settle()
		expect(api.listFindings.mock.calls.length).toBe(calls)
		await byId(wrapper, "talon-ops-more").trigger("click")
		await settle()
		expect(api.listFindings.mock.calls.at(-1)?.[0]).toMatchObject({ order: "recent", cursor: "1729740000000000.1" })
	})

	it("a Talon without the summary has no severity order: recently changed, and Severity disabled", async () => {
		signInAs(AuthUserRole.Analyst)
		api.summary.mockImplementation(() => refusal(404, { detail: OLD_TALON_OPS_TEXT, code: "unsupported" }))
		const wrapper = render()
		await settle()
		expect(api.listFindings.mock.calls.at(-1)?.[0]).toMatchObject({ order: "recent", cursor: null })
		expect(wrapper.findComponent(NRadioGroup).props("value")).toBe("recent")
		const severity = byId(wrapper, "talon-ops-order-severity")
		expect(severity.attributes("title")).toBe(SEVERITY_ORDER_UNAVAILABLE)
		expect(severity.find("input").attributes("disabled")).toBeDefined()
	})
})

describe("grouping by customer", () => {
	it("puts the rows under their customer, platform findings under Platform, and keeps paging", async () => {
		signInAs(AuthUserRole.Admin)
		api.listFindings.mockImplementationOnce(() =>
			ok({
				success: true,
				message: "",
				items: [finding(1), finding(2, { customer_code: null }), finding(3, { customer_code: "GLOBEX" })],
				next_cursor: "100.3",
				dropped: 0
			})
		)
		const wrapper = render()
		await settle()
		expect(byId(wrapper, "talon-ops-group-ACME").exists()).toBe(false)
		switchWith(wrapper, "talon-ops-group").vm.$emit("update:value", true)
		await settle()
		const groups = wrapper.findAll('[data-testid^="talon-ops-group-"]').filter(g => g.element.tagName === "SECTION")
		expect(groups.map(g => g.find('[data-testid="talon-ops-group-label"]').text())).toEqual([
			"ACME",
			"Platform",
			"GLOBEX"
		])
		expect(byId(wrapper, "talon-ops-group-platform").find('[data-testid="talon-ops-row-2"]').exists()).toBe(true)
		api.listFindings.mockImplementationOnce(() =>
			ok({ success: true, message: "", items: [finding(4)], next_cursor: null, dropped: 0 })
		)
		await byId(wrapper, "talon-ops-more").trigger("click")
		await settle()
		expect(byId(wrapper, "talon-ops-group-ACME").find('[data-testid="talon-ops-row-4"]').exists()).toBe(true)
	})
})

describe("bulk actions", () => {
	function tableOf(wrapper: Wrapper, index = 0) {
		return wrapper.findAllComponents(DataTable)[index]
	}

	async function select(wrapper: Wrapper, keys: number[]) {
		tableOf(wrapper).vm.$emit("update:checkedRowKeys", keys)
		await settle()
	}

	it("lets only rows an action applies to be selected", async () => {
		signInAs(AuthUserRole.Analyst)
		rows(finding(1), finding(2, { status: "resolved" }))
		const wrapper = render()
		await settle()
		const [selection] = tableOf(wrapper).props("columns") as {
			type?: string
			disabled: (row: unknown) => boolean
		}[]
		expect(selection.type).toBe("selection")
		expect(selection.disabled(finding(1))).toBe(false)
		expect(selection.disabled(finding(2, { status: "resolved" }))).toBe(true)
	})

	it("acknowledges the eligible selected rows one request each, lists the failures, and refreshes once", async () => {
		signInAs(AuthUserRole.Analyst)
		rows(finding(1), finding(2), finding(3, { status: "acknowledged" }))
		api.acknowledge.mockImplementation((id: number) =>
			id === 2
				? refusal(409, { detail: "Talon refused the request in the finding's current state", code: "conflict" })
				: ok({ success: true, message: "", finding: finding(id, { status: "acknowledged" }) })
		)
		const wrapper = render()
		await settle()
		await select(wrapper, [1, 2, 3])
		expect(byId(wrapper, "talon-ops-bulk-count").text()).toBe("3 selected")
		// The acknowledged one can be muted, not acknowledged again.
		expect(byId(wrapper, "talon-ops-bulk-acknowledge").text()).toBe("Acknowledge 2")
		expect(byId(wrapper, "talon-ops-bulk-mute").text()).toBe("Mute 3")
		const [listed, counted] = [api.listFindings.mock.calls.length, api.summary.mock.calls.length]
		await byId(wrapper, "talon-ops-bulk-acknowledge").trigger("click")
		await settle()
		expect(api.acknowledge.mock.calls).toEqual([
			[1, "ACME"],
			[2, "ACME"]
		])
		expect(byId(wrapper, "talon-ops-bulk-summary").text()).toBe("1 acknowledged, 1 failed")
		const failures = byId(wrapper, "talon-ops-bulk-failures").findAll("li")
		expect(failures).toHaveLength(1)
		expect(failures[0].text()).toContain("host-2: not seen by Wazuh for 5 days")
		expect(failures[0].text()).toContain("current state")
		expect(api.listFindings.mock.calls.length).toBe(listed + 1)
		expect(api.summary.mock.calls.length).toBe(counted + 1)
		// The refresh cleared the selection; the report stays.
		expect(byId(wrapper, "talon-ops-bulk-count").exists()).toBe(false)
		expect(byId(wrapper, "talon-ops-bulk-report").exists()).toBe(true)
	})

	it("mutes the selected rows until a preset, with each finding's stored customer", async () => {
		signInAs(AuthUserRole.Analyst)
		rows(finding(1), finding(2, { customer_code: "DOTTED.CO" }))
		const wrapper = render()
		await settle()
		await select(wrapper, [1, 2])
		await byId(wrapper, "talon-ops-bulk-mute-preset-30").trigger("click")
		await byId(wrapper, "talon-ops-bulk-mute").trigger("click")
		await settle()
		expect(api.mute).toHaveBeenCalledTimes(2)
		const [[id1, until, code1], [id2, , code2]] = api.mute.mock.calls
		expect([id1, code1, id2, code2]).toEqual([1, "ACME", 2, "DOTTED.CO"])
		const days = (Date.parse(until) - Date.now()) / (24 * 3600 * 1000)
		expect(days).toBeGreaterThan(29)
		expect(days).toBeLessThanOrEqual(31)
		expect(byId(wrapper, "talon-ops-bulk-summary").text()).toBe("2 muted, 0 failed")
		expect(byId(wrapper, "talon-ops-bulk-failures").exists()).toBe(false)
	})

	it("takes at most 50 findings", async () => {
		signInAs(AuthUserRole.Analyst)
		const many = Array.from({ length: 51 }, (_, i) => finding(i + 1))
		rows(...many)
		const wrapper = render()
		await settle()
		await select(
			wrapper,
			many.map(f => f.id)
		)
		expect(byId(wrapper, "talon-ops-bulk-cap").text()).toContain("at most 50")
		expect(byId(wrapper, "talon-ops-bulk-acknowledge").attributes("disabled")).toBeDefined()
		expect(byId(wrapper, "talon-ops-bulk-mute").attributes("disabled")).toBeDefined()
		await byId(wrapper, "talon-ops-bulk-acknowledge").trigger("click")
		await settle()
		expect(api.acknowledge).not.toHaveBeenCalled()
		await select(
			wrapper,
			many.slice(0, 50).map(f => f.id)
		)
		expect(byId(wrapper, "talon-ops-bulk-cap").exists()).toBe(false)
		await byId(wrapper, "talon-ops-bulk-acknowledge").trigger("click")
		await settle()
		expect(api.acknowledge).toHaveBeenCalledTimes(50)
	})

	it("clears the selection when the stale filter hides rows, and acts only on the rows shown", async () => {
		signInAs(AuthUserRole.Analyst)
		rows(finding(1), finding(2, { stale_since: T }))
		const wrapper = render()
		await settle()
		await select(wrapper, [1, 2])
		expect(byId(wrapper, "talon-ops-bulk-count").text()).toBe("2 selected")
		await byId(wrapper, "talon-ops-summary-stale").trigger("click")
		await settle()
		expect(byId(wrapper, "talon-ops-bulk-count").exists()).toBe(false)
		// A hidden row's key can't come back with the shown table's selection either.
		await select(wrapper, [1, 2])
		expect(byId(wrapper, "talon-ops-bulk-count").text()).toBe("1 selected")
		await byId(wrapper, "talon-ops-bulk-acknowledge").trigger("click")
		await settle()
		expect(api.acknowledge.mock.calls).toEqual([[2, "ACME"]])
	})

	it("keeps its report when the refresh afterwards fails", async () => {
		signInAs(AuthUserRole.Analyst)
		rows(finding(1))
		const wrapper = render()
		await settle()
		await select(wrapper, [1])
		api.listFindings.mockImplementation(() => refusal(502, { detail: "Talon could not be reached", code: "unavailable" }))
		await byId(wrapper, "talon-ops-bulk-acknowledge").trigger("click")
		await settle()
		expect(wrapper.text()).toContain("Talon could not be reached")
		expect(byId(wrapper, "talon-ops-bulk-summary").text()).toBe("1 acknowledged, 0 failed")
	})

	it("keeps each group's selection when grouped", async () => {
		signInAs(AuthUserRole.Analyst)
		rows(finding(1), finding(2, { customer_code: "DOTTED.CO" }))
		const wrapper = render()
		await settle()
		switchWith(wrapper, "talon-ops-group").vm.$emit("update:value", true)
		await settle()
		tableOf(wrapper, 0).vm.$emit("update:checkedRowKeys", [1])
		await settle()
		tableOf(wrapper, 1).vm.$emit("update:checkedRowKeys", [2])
		await settle()
		expect(byId(wrapper, "talon-ops-bulk-count").text()).toBe("2 selected")
	})
})

describe("links out", () => {
	function linksIn(wrapper: Wrapper, testId: string) {
		return byId(wrapper, testId)
			.findAllComponents(RouterLinkStub)
			.map((link: VueWrapper) => (link.props() as { to: unknown }).to)
	}

	it("puts the finding's link in the title cell, without opening the drawer", async () => {
		signInAs(AuthUserRole.Analyst)
		const wrapper = render()
		await settle()
		const link = byId(wrapper, "talon-ops-row-1").findComponent(RouterLinkStub)
		expect(link.props("to")).toEqual({ name: "Agent", params: { id: "001" } })
		await link.trigger("click")
		await settle()
		expect(api.getFinding).not.toHaveBeenCalled()
	})

	it("lists the agent and the customer in the drawer, from the evidence ids", async () => {
		signInAs(AuthUserRole.Analyst)
		const wrapper = render()
		await settle()
		await byId(wrapper, "talon-ops-row-1").trigger("click")
		await settle()
		expect(linksIn(wrapper, "talon-ops-detail-links")).toEqual([
			{ name: "Agent", params: { id: "001" } },
			{ name: "Customer", params: { code: "ACME" } }
		])
	})

	it("links nothing from a rejected id or the model's text", async () => {
		signInAs(AuthUserRole.Analyst)
		const tricky = {
			title: "host: see /agents/999",
			why: "Open /agents/999 and /customers/EVIL",
			recommendation: "[fix](/indices/management) or /alerts",
			evidence: { agent_id: "../../users", agent_name: "x" }
		}
		rows(finding(1, tricky))
		api.getFinding.mockImplementation((id: number) =>
			ok({ success: true, message: "", finding: finding(id, tricky) })
		)
		const wrapper = render()
		await settle()
		// No agent link: the title cell falls back to the customer.
		expect(byId(wrapper, "talon-ops-row-1").findComponent(RouterLinkStub).props("to")).toEqual({
			name: "Customer",
			params: { code: "ACME" }
		})
		await byId(wrapper, "talon-ops-row-1").trigger("click")
		await settle()
		expect(linksIn(wrapper, "talon-ops-detail-links")).toEqual([{ name: "Customer", params: { code: "ACME" } }])
		expect(JSON.stringify(wrapper.findAllComponents(RouterLinkStub).map(l => l.props("to")))).not.toMatch(
			/999|EVIL|users/
		)
	})
})

describe("states", () => {
	it("no job enabled in Talon: says ops jobs are off, with the TALON_OPS_JOBS hint", async () => {
		signInAs(AuthUserRole.Analyst)
		api.listJobs.mockImplementation(() =>
			ok({ success: true, message: "", any_enabled: false, items: [job("quiet_endpoints", { enabled: false })] })
		)
		const wrapper = render()
		await settle()
		const off = byId(wrapper, "talon-ops-off")
		expect(off.attributes("title") ?? off.text()).toBeTruthy()
		expect(wrapper.text()).toContain(OPS_OFF_TITLE)
		expect(off.text()).toContain("TALON_OPS_JOBS")
	})

	it.each([
		[{ detail: "Not Found" }, V2_OFF_TEXT],
		[{ detail: OLD_TALON_OPS_TEXT, code: "unsupported" }, OLD_TALON_OPS_TEXT]
	])("v2 off or an old Talon: only the notice", async (body, text) => {
		signInAs(AuthUserRole.Analyst)
		api.listJobs.mockImplementation(() => refusal(404, body))
		const wrapper = render()
		await settle()
		expect(byId(wrapper, "talon-ops-problem").text()).toContain(text)
		expect(byId(wrapper, "talon-ops-findings").exists()).toBe(false)
	})

	it("a role without access asks nothing", async () => {
		signInAs(AuthUserRole.CustomerUser)
		const wrapper = render()
		await settle()
		expect(byId(wrapper, "talon-ops-not-for-role").exists()).toBe(true)
		expect(api.listJobs).not.toHaveBeenCalled()
		expect(api.listFindings).not.toHaveBeenCalled()
	})
})

describe("history (OP-3)", () => {
	async function opened(role: AuthUserRole, overrides: Record<string, unknown> = {}) {
		signInAs(role)
		const row = finding(1, overrides)
		rows(row)
		api.getFinding.mockImplementation(() => ok({ success: true, message: "", finding: row }))
		const wrapper = render()
		await settle()
		await byId(wrapper, "talon-ops-row-1").trigger("click")
		await settle()
		return wrapper
	}

	const FIRST = "2026-10-20T06:00:00Z"
	function runAt(i: number, at: string, overrides: Record<string, unknown> = {}) {
		return opsRun("ACME", { id: `r${i}`, tick: at, started_at: at, finished_at: at, ...overrides })
	}

	it("reads the job's runs for the finding's customer and shows those since it was first seen", async () => {
		api.listRuns.mockImplementation(() =>
			ok({
				success: true,
				message: "",
				dropped: 0,
				items: [
					runAt(1, "2026-10-24T06:00:30Z", { status: "partial", error: "<b>indexer timeout</b>" }),
					runAt(2, "2026-10-21T06:00:30Z"),
					runAt(3, "2026-10-19T06:00:30Z"),
					runAt(4, "2026-10-23T06:00:30Z", { customer_code: "GLOBEX" }),
					runAt(5, "2026-10-23T06:00:30Z", { job: "silent_log_sources" })
				]
			})
		)
		const wrapper = await opened(AuthUserRole.Analyst, { first_seen: FIRST, stale_since: "2026-10-23T06:00:00Z" })
		expect(api.listRuns).toHaveBeenCalledWith(
			{ job: "quiet_endpoints", customer_code: "ACME", limit: 30 },
			expect.anything()
		)
		const runs = wrapper.findAll('[data-testid="talon-ops-history-run"]')
		expect(runs).toHaveLength(2)
		expect(runs[0].text()).toContain("partial")
		expect(runs[0].text()).toContain("1 new, 1 updated, 0 resolved")
		expect(runs[0].text()).toContain("<b>indexer timeout</b>")
		expect(runs[0].find("b").exists()).toBe(false)
		expect(byId(wrapper, "talon-ops-history-first-seen").find("time").attributes("title")).toBe("2026-10-20 06:00 UTC")
		expect(byId(wrapper, "talon-ops-history-stale").exists()).toBe(true)
		expect(byId(wrapper, "talon-ops-history").text()).toContain("doesn't record a finding's severity changes")
		expect(byId(wrapper, "talon-ops-history").text().toLowerCase()).not.toContain("severity changed")
	})

	it("shows at most 30 runs", async () => {
		const items = Array.from({ length: 40 }, (_, i) => runAt(i, new Date(Date.parse("2026-10-24T00:00:00Z") - i * 3600_000).toISOString()))
		api.listRuns.mockImplementation(() => ok({ success: true, message: "", dropped: 0, items }))
		const wrapper = await opened(AuthUserRole.Analyst, { first_seen: FIRST })
		expect(wrapper.findAll('[data-testid="talon-ops-history-run"]')).toHaveLength(30)
	})

	it("says when the runs can't be read", async () => {
		api.listRuns.mockImplementation(() => refusal(502, { detail: "Talon didn't answer", code: "unavailable" }))
		const wrapper = await opened(AuthUserRole.Analyst)
		expect(byId(wrapper, "talon-ops-history-error").text()).toContain("Talon didn't answer")
		expect(byId(wrapper, "talon-ops-detail-title").exists()).toBe(true)
	})

	it("doesn't read the runs again when an action replaces the finding", async () => {
		const wrapper = await opened(AuthUserRole.Analyst, { first_seen: FIRST })
		const historyReads = () => api.listRuns.mock.calls.filter(([q]) => (q as { limit?: number }).limit === 30).length
		expect(historyReads()).toBe(1)
		await byId(wrapper, "talon-ops-acknowledge").trigger("click")
		await settle()
		expect(byId(wrapper, "talon-ops-detail-status").text()).toContain("Acknowledged")
		expect(historyReads()).toBe(1)
		expect(byId(wrapper, "talon-ops-history-loading").exists()).toBe(false)
		expect(wrapper.findAll('[data-testid="talon-ops-history-run"]')).toHaveLength(1)
	})

	it("doesn't read a disk_forecast finding's runs again after an action either", async () => {
		const evidence = { node: "node-1", used_gb: 700, total_gb: 1000, slope_gb_per_day: 2, thresholds_used_pct: { low: 85 } }
		api.acknowledge.mockImplementation((id: number) =>
			ok({
				success: true,
				message: "",
				finding: finding(id, { job: "disk_forecast", kind: "disk_forecast", customer_code: null, evidence: { ...evidence }, status: "acknowledged" })
			})
		)
		const wrapper = await opened(AuthUserRole.Admin, { job: "disk_forecast", kind: "disk_forecast", customer_code: null, evidence })
		const diskReads = () => api.listRuns.mock.calls.filter(([q]) => (q as { job?: string; limit?: number }).limit === 200).length
		expect(diskReads()).toBe(1)
		await byId(wrapper, "talon-ops-acknowledge").trigger("click")
		await settle()
		expect(diskReads()).toBe(1)
	})

	it("marks the runs that started after the finding resolved", async () => {
		api.listRuns.mockImplementation(() =>
			ok({
				success: true,
				message: "",
				dropped: 0,
				items: [
					runAt(1, "2026-10-23T06:00:30Z"),
					runAt(2, "2026-10-22T06:00:30Z", { started_at: "2026-10-22T06:00:00Z", tick: "2026-10-22T06:00:00Z" }), // resolved it
					runAt(3, "2026-10-21T06:00:30Z")
				]
			})
		)
		const wrapper = await opened(AuthUserRole.Analyst, {
			first_seen: FIRST,
			status: "resolved",
			resolved_at: "2026-10-22T06:00:20Z",
			resolved_reason: "cleared"
		})
		const runs = wrapper.findAll('[data-testid="talon-ops-history-run"]')
		expect(runs.map(r => r.find('[data-testid="talon-ops-history-after-resolved"]').exists())).toEqual([true, false, false])
		expect(byId(wrapper, "talon-ops-history-resolved").text()).toContain("(cleared)")
	})

	it("reads a platform finding's runs without a customer, for an admin only", async () => {
		const platform = { customer_code: null, job: "cluster_health", kind: "cluster_status", evidence: { status: "yellow" } }
		const analyst = await opened(AuthUserRole.Analyst, platform)
		expect(byId(analyst, "talon-ops-history-admins-only").exists()).toBe(true)
		expect(api.listRuns).not.toHaveBeenCalledWith(expect.objectContaining({ job: "cluster_health" }), expect.anything())
		analyst.unmount()

		api.listRuns.mockReset()
		api.listRuns.mockImplementation(() =>
			ok({ success: true, message: "", dropped: 0, items: [opsRun(null, { job: "cluster_health" })] })
		)
		const admin = await opened(AuthUserRole.Admin, platform)
		expect(api.listRuns).toHaveBeenCalledWith({ job: "cluster_health", limit: 30 }, expect.anything())
		expect(admin.findAll('[data-testid="talon-ops-history-run"]')).toHaveLength(1)
	})
})

describe("the jobs table's recent runs (OP-3)", () => {
	async function expanded() {
		signInAs(AuthUserRole.Analyst)
		const wrapper = render()
		await settle()
		await byId(wrapper, "talon-ops-jobs-toggle").trigger("click")
		return wrapper
	}

	function recentCalls() {
		return api.listRuns.mock.calls.filter(([query]) => (query as { limit?: number }).limit === 10)
	}

	it("reads a job's last 10 runs on its first expand, and keeps them until Refresh", async () => {
		const wrapper = await expanded()
		expect(recentCalls()).toHaveLength(0)
		await byId(wrapper, "talon-ops-job-runs-toggle-quiet_endpoints").trigger("click")
		await settle()
		expect(recentCalls()).toEqual([[{ job: "quiet_endpoints", limit: 10 }, expect.anything()]])
		expect(wrapper.findAll('[data-testid="talon-ops-job-recent-run"]')).toHaveLength(1)

		await byId(wrapper, "talon-ops-job-runs-toggle-quiet_endpoints").trigger("click")
		await byId(wrapper, "talon-ops-job-runs-toggle-quiet_endpoints").trigger("click")
		await settle()
		expect(recentCalls()).toHaveLength(1)

		await byId(wrapper, "talon-ops-jobs-refresh").trigger("click")
		await settle()
		expect(recentCalls()).toHaveLength(2)
		expect(wrapper.findAll('[data-testid="talon-ops-job-recent-run"]')).toHaveLength(1)
	})

	it("doesn't cache a failed read: the next expand tries again", async () => {
		api.listRuns.mockImplementationOnce(() => refusal(502, { detail: "Talon didn't answer", code: "unavailable" }))
		const wrapper = await expanded()
		const toggle = () => byId(wrapper, "talon-ops-job-runs-toggle-quiet_endpoints").trigger("click")
		await toggle()
		await settle()
		expect(byId(wrapper, "talon-ops-job-recent-error-quiet_endpoints").exists()).toBe(true)
		await toggle()
		await toggle()
		await settle()
		expect(recentCalls()).toHaveLength(2)
		expect(byId(wrapper, "talon-ops-job-recent-error-quiet_endpoints").exists()).toBe(false)
		expect(wrapper.findAll('[data-testid="talon-ops-job-recent-run"]')).toHaveLength(1)
		await toggle()
		await toggle()
		await settle()
		expect(recentCalls()).toHaveLength(2)
	})

	it("shows at most 10 runs and says when they can't be read", async () => {
		api.listRuns.mockImplementationOnce(() =>
			ok({ success: true, message: "", dropped: 0, items: Array.from({ length: 12 }, (_, i) => opsRun("ACME", { id: `r${i}` })) })
		)
		const wrapper = await expanded()
		await byId(wrapper, "talon-ops-job-runs-toggle-quiet_endpoints").trigger("click")
		await settle()
		expect(wrapper.findAll('[data-testid="talon-ops-job-recent-run"]')).toHaveLength(10)

		api.listRuns.mockImplementationOnce(() => refusal(502, { detail: "Talon didn't answer", code: "unavailable" }))
		await byId(wrapper, "talon-ops-job-runs-toggle-silent_log_sources").trigger("click")
		await settle()
		expect(byId(wrapper, "talon-ops-job-recent-error-silent_log_sources").text()).toContain("Talon didn't answer")
	})
})
