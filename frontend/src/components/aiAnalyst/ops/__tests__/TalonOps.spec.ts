import type { VNodeChild } from "vue"
/**
 * The Ops tab (`TalonOps.vue` and its sections) against a mocked API: the findings table (open by
 * default, filters, cursor paging, every value as text), the detail drawer (the evidence as a list or
 * JSON, the artifact copyable, `why` and `recommendation` as plain text, never HTML), the actions with
 * the finding's stored customer, the mute window and its presets, the stale marker, the jobs panel
 * (collapsed under a summary line, schedules in words, per-customer last runs, run now for an admin
 * only, polling its runs afterwards), and the states: Ops jobs off in Talon, Talon v2 off, an old
 * Talon, a role without access.
 */
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils"
import { AxiosError, AxiosHeaders } from "axios"
import { NSelect, NSwitch } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import { resetCustomerOptions } from "@/composables/useCustomerOptions"
import { useAuthStore } from "@/stores/auth"
import { AuthUserRole } from "@/types/auth"
import { OLD_TALON_OPS_TEXT, OPS_OFF_TITLE, RUN_POLL_MS, RUN_WATCH_MS, STALE_TEXT, V2_OFF_TEXT } from "../ops"
import TalonOps from "../TalonOps.vue"

const api = {
	listFindings: vi.fn(),
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

function ok<T>(data: T) {
	return Promise.resolve({ data })
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
			stubs: { Drawer, DrawerContent: Passthrough, DataTable, DatePicker, Tooltip, Icon: true }
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
		expect(analyst.findAllComponents(NSwitch)).toHaveLength(0)
		analyst.unmount()

		signInAs(AuthUserRole.Admin)
		const admin = render()
		await settle()
		admin.findComponent(NSwitch).vm.$emit("update:value", true)
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
		expect(status.find('[data-testid="tooltip-content"]').text()).toBe(STALE_TEXT)
		expect(STALE_TEXT).toContain("can't clear")
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

	it("shows the evidence as a list, or as JSON", async () => {
		const wrapper = await opened()
		const list = byId(wrapper, "talon-ops-detail-evidence")
		expect(list.text()).toContain("agent_id")
		expect(list.text()).toContain("wazuh_quiet")
		await byId(wrapper, "talon-ops-detail-evidence-toggle").trigger("click")
		expect(JSON.parse(byId(wrapper, "talon-ops-detail-evidence-json").text())).toMatchObject({ agent_id: "001" })
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
			const day = 24 * 3600 * 1000
			await byId(wrapper, "talon-ops-mute-preset-1").trigger("click")
			expect((picker.element as HTMLInputElement).value).toBe(String(now + day))
			await byId(wrapper, "talon-ops-mute-preset-7").trigger("click")
			expect((picker.element as HTMLInputElement).value).toBe(String(now + 7 * day))
			await byId(wrapper, "talon-ops-mute-preset-30").trigger("click")
			expect((picker.element as HTMLInputElement).value).toBe(String(now + 30 * day))
			expect(byId(wrapper, "talon-ops-mute").attributes("disabled")).toBeUndefined()
			await byId(wrapper, "talon-ops-mute").trigger("click")
			await settle()
			expect(api.mute).toHaveBeenCalledWith(1, new Date(now + 30 * day).toISOString(), "ACME")
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
		expect(lines[0].text()).toContain("ACME")
		expect(lines[0].text()).toContain("ok")
		expect(lines[0].text()).toContain("2 new, 0 updated, 1 resolved")
		expect(lines[1].text()).toContain("BETA")
		expect(lines[1].text()).toContain("partial")
		expect(lines[1].text()).toContain("? new, 1 updated, 0 resolved")
		expect(lines[1].text()).toContain("the indexer timed out")
		await toggle.trigger("click")
		expect(byId(wrapper, "talon-ops-job-runs-quiet_endpoints").exists()).toBe(false)
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
	let runs: ReturnType<typeof opsRun>[]

	beforeEach(() => {
		// Only the clocks: flushPromises still uses the real setImmediate.
		vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout", "Date"], now: CLICK })
		runs = [opsRun("ACME")]
		api.listRuns.mockImplementation(() => ok({ success: true, message: "", items: runs, dropped: 0 }))
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

	const fresh = (customer: string, overrides: Record<string, unknown> = {}) =>
		opsRun(customer, {
			id: `quiet_endpoints:${customer}:2026-10-24T08:00:00Z`,
			triggered_by: "manual",
			finished_at: "2026-10-24T08:00:20Z",
			new: 2,
			updated: 1,
			resolved: 3,
			...overrides
		})

	it("reloads the jobs and the findings when the run finishes, and says what it found", async () => {
		const wrapper = await clicked()
		expect(api.listRuns).toHaveBeenCalledWith({ job: "quiet_endpoints", limit: 200 }, expect.anything())
		expect(byId(wrapper, "talon-ops-run-message").text()).toContain("queued")
		expect(byId(wrapper, "talon-ops-run-quiet_endpoints").attributes("disabled")).toBeDefined()
		const jobsCalls = api.listJobs.mock.calls.length
		const findingsCalls = api.listFindings.mock.calls.length

		await tick()
		expect(api.listRuns).toHaveBeenCalledTimes(2)
		expect(api.listJobs).toHaveBeenCalledTimes(jobsCalls)

		runs = [fresh("ACME"), ...runs]
		await tick()
		expect(api.listJobs).toHaveBeenCalledTimes(jobsCalls + 1)
		expect(api.listFindings).toHaveBeenCalledTimes(findingsCalls + 1)
		const message = byId(wrapper, "talon-ops-run-message")
		expect(message.text()).toBe("Endpoints gone quiet finished: 2 new, 1 updated, 3 resolved.")
		expect(byId(wrapper, "talon-ops-run-quiet_endpoints").attributes("disabled")).toBeUndefined()

		const polls = api.listRuns.mock.calls.length
		await tick(RUN_WATCH_MS)
		expect(api.listRuns).toHaveBeenCalledTimes(polls)
	})

	it("waits for every customer's run, saying what came in so far", async () => {
		const wrapper = await clicked([
			job("quiet_endpoints", { last_runs: [opsRun("ACME"), opsRun("BETA", { id: "beta-old" })] })
		])
		runs = [fresh("ACME"), ...runs]
		await tick()
		expect(byId(wrapper, "talon-ops-run-message").text()).toBe(
			"Endpoints gone quiet: 2 new, 1 updated, 3 resolved so far (1 of 2 customers); still running."
		)
		runs = [fresh("BETA", { status: "partial", new: 0, updated: 0, resolved: 1 }), ...runs]
		await tick()
		expect(byId(wrapper, "talon-ops-run-message").text()).toBe(
			"Endpoints gone quiet finished (partial): 2 new, 1 updated, 4 resolved."
		)
	})

	it("gives up after two minutes: still running, refresh later", async () => {
		const wrapper = await clicked()
		const jobsCalls = api.listJobs.mock.calls.length
		await tick(RUN_WATCH_MS - RUN_POLL_MS)
		expect(byId(wrapper, "talon-ops-run-message").text()).toContain("queued")
		await tick()
		expect(byId(wrapper, "talon-ops-run-message").text()).toBe(
			"Endpoints gone quiet is still running; refresh later."
		)
		expect(api.listJobs).toHaveBeenCalledTimes(jobsCalls)
		const polls = api.listRuns.mock.calls.length
		expect(polls).toBe(1 + RUN_WATCH_MS / RUN_POLL_MS)
		await tick(RUN_WATCH_MS)
		expect(api.listRuns).toHaveBeenCalledTimes(polls)
		expect(byId(wrapper, "talon-ops-run-quiet_endpoints").attributes("disabled")).toBeUndefined()
	})

	it("keeps polling past a failed read", async () => {
		const wrapper = await clicked()
		api.listRuns.mockImplementationOnce(() =>
			refusal(502, { detail: "Talon could not be reached", code: "unavailable" })
		)
		await tick()
		runs = [fresh("ACME"), ...runs]
		await tick()
		expect(byId(wrapper, "talon-ops-run-message").text()).toContain("finished")
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
		expect(byId(wrapper, "talon-ops-run-message").text()).toBe("the job is not enabled (TALON_OPS_JOBS)")
		const polls = api.listRuns.mock.calls.length
		await tick(RUN_WATCH_MS)
		expect(api.listRuns).toHaveBeenCalledTimes(polls)
		expect(byId(wrapper, "talon-ops-run-quiet_endpoints").attributes("disabled")).toBeUndefined()
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
