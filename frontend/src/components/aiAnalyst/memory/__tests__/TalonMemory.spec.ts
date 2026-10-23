import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils"
/**
 * The Memory tab (`TalonMemory.vue` and its sections), against a mocked API: the customer picker
 * seeded with the caller's one customer, the tiles and breakdowns, the list with its filters, a
 * debounced search and cursor paging; the detail drawer (markdown through `Markdown` with images
 * off, source links to the job and the alert, why it is hidden, Forget only when allowed, after a
 * confirm in a modal); the assets' timeline; "My chat memory" (the caller's own, forget with a
 * confirm); and the states: loading, empty, an error with a retry, Talon v2 off, an old Talon.
 */
import { AxiosError, AxiosHeaders } from "axios"
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import { resetCustomerOptions } from "@/composables/useCustomerOptions"
import { useAuthStore } from "@/stores/auth"
import { AuthUserRole } from "@/types/auth"
import { OLD_TALON_MEMORY_TEXT, SEARCH_DEBOUNCE_MS, V2_OFF_TEXT } from "../memory"
import TalonMemory from "../TalonMemory.vue"

const api = {
	getStats: vi.fn(),
	listDrawers: vi.fn(),
	getDrawer: vi.fn(),
	forgetDrawer: vi.fn(),
	listAssets: vi.fn(),
	getAssetTimeline: vi.fn(),
	listMyChatMemory: vi.fn(),
	forgetMyChatMemory: vi.fn()
}
const getCustomers = vi.fn()

vi.mock("@/api", () => ({
	default: {
		talonMemory: new Proxy(
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

const ONE_OFF = "drawer_ACME_false_positives_0123456789abcdef01234567"
const DURABLE = "drawer_ACME_alerts_aaaaaaaaaaaaaaaaaaaaaaaa"

function ok<T>(data: T) {
	return Promise.resolve({ data })
}

function refusal(status: number, data: unknown) {
	const headers = new AxiosHeaders()
	return Promise.reject(
		new AxiosError("x", "ERR", undefined, undefined, { status, statusText: "", data, headers, config: { headers } })
	)
}

function stats() {
	return {
		success: true,
		customer_code: "ACME",
		total: 42,
		checked_at: "2026-10-22T08:00:00Z",
		rooms: { alerts: 10, false_positives: 12, threat_intel: 5, assets: 8, environment: 6, other: null },
		sources: { investigation: 20, review_durable: 6, review_one_off: 10, chat_remember: 5, other: 1 },
		testing_hidden: 3,
		growth: [
			{ date: "2026-10-20", filed: 2 },
			{ date: "2026-10-21", filed: null },
			{ date: "2026-10-22", filed: 4 }
		]
	}
}

function item(id = ONE_OFF, overrides = {}) {
	return {
		drawer_id: id,
		openable: true,
		room: "false_positives",
		source: "review_one_off",
		source_ref: { job_id: "copilot-inv-1-1760601600000", alert_id: 7 },
		filed_at: "2026-10-21T10:00:00Z",
		durable: false,
		testing_hidden: false,
		visible_to_investigations: true,
		preview: `Preview of ${id}`,
		...overrides
	}
}

function drawer(overrides = {}) {
	return {
		...item(),
		content: '# Lesson\n\n<img src=x onerror="alert(1)"> ![pixel](https://evil.invalid/p.png)',
		forgettable: true,
		why_not_forgettable: null,
		why_hidden: null,
		...overrides
	}
}

// ── stubs: naive's tabs, drawer and modal without teleports or transitions ────

const NAMES = ["customer", "chat"]
const Tabs = defineComponent({
	emits: ["update:value"],
	setup:
		(_, { slots, emit }) =>
		() =>
			h("div", [
				...NAMES.map(name =>
					h("button", { "data-open": name, onClick: () => emit("update:value", name) }, name)
				),
				slots.default?.()
			])
})
const TabPane = defineComponent({
	props: { name: { type: String, default: "" } },
	setup:
		(props, { slots }) =>
		() =>
			h("section", { "data-pane": props.name }, slots.default?.())
})
function Show(testId: string) {
	return defineComponent({
		props: { show: { type: Boolean, default: false } },
		setup:
			(props, { slots }) =>
			() =>
				props.show ? h("div", { "data-testid": testId }, [slots.default?.(), slots.footer?.()]) : null
	})
}
const Passthrough = defineComponent({
	setup:
		(_, { slots }) =>
		() =>
			h("div", slots.default?.())
})
/** Markdown as its props: the source as text, and whether images are off. */
const MarkdownStub = defineComponent({
	props: { source: { type: String, default: "" }, noImages: { type: Boolean, default: false } },
	setup: props => () =>
		h("pre", { "data-testid": "markdown", "data-no-images": String(props.noImages) }, props.source)
})
const RouterLinkStub = defineComponent({
	props: { to: { type: Object, required: true } },
	setup:
		(props, { slots }) =>
		() =>
			h("a", { "data-to": JSON.stringify(props.to) }, slots.default?.())
})
const VChartStub = defineComponent({ setup: () => () => h("div", { "data-testid": "talon-memory-growth" }) })

vi.mock("vue-echarts", async () => {
	const vue = await import("vue")
	return { default: vue.defineComponent({ setup: () => () => vue.h("div", { "data-testid": "vchart" }) }) }
})

function render() {
	return mount(TalonMemory, {
		global: {
			stubs: {
				Tabs,
				TabPane,
				Drawer: Show("drawer-stub"),
				DrawerContent: Passthrough,
				Modal: Show("modal-stub"),
				RouterLink: RouterLinkStub,
				VChart: VChartStub,
				Markdown: MarkdownStub,
				Icon: true
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
	return wrapper.findAll(`[data-testid="${id}"]`)
}

enableAutoUnmount(afterEach)

beforeEach(() => {
	setActivePinia(createPinia())
	resetCustomerOptions()
	for (const fn of Object.values(api)) fn.mockReset()
	getCustomers.mockReset()
	getCustomers.mockReturnValue(ok({ customers: [{ customer_code: "ACME", customer_name: "Acme" }] }))
	api.getStats.mockImplementation(() => ok(stats()))
	api.listDrawers.mockImplementation(() =>
		ok({
			success: true,
			items: [item(), item(DURABLE, { source: "investigation", durable: true, testing_hidden: true })],
			next_cursor: "c1"
		})
	)
	api.getDrawer.mockImplementation(() => ok(drawer()))
	api.listAssets.mockImplementation(() =>
		ok({ success: true, items: [{ asset: "SRV-01", openable: true, alerts: 4, iocs: 2, last_seen: null }] })
	)
	api.getAssetTimeline.mockImplementation(() =>
		ok({
			success: true,
			asset: "SRV-01",
			facts: [
				{ subject: "SRV-01", predicate: "runs", object: "vssadmin", valid_from: "2026-10-02", valid_to: null },
				{
					subject: "SRV-01",
					predicate: "owned by",
					object: "IT",
					valid_from: "2026-09-01",
					valid_to: "2026-10-01"
				}
			]
		})
	)
	api.listMyChatMemory.mockImplementation(() =>
		ok({
			success: true,
			items: [
				{ drawer_id: "drawer_chat_1", openable: true, filed_at: null, preview: "Prefers UTC", thread_id: null }
			]
		})
	)
	signInAs(AuthUserRole.Analyst)
})

describe("the Memory tab", () => {
	it("picks the caller's one customer and shows the tiles, breakdowns and the list", async () => {
		const wrapper = render()
		await settle()
		expect(api.getStats).toHaveBeenCalledWith("ACME", expect.anything())
		expect(byId(wrapper, "talon-memory-total")[0].text()).toContain("42")
		expect(byId(wrapper, "talon-memory-filed")[0].text()).toContain("6")
		expect(byId(wrapper, "talon-memory-hidden")[0].text()).toContain("3")
		expect(byId(wrapper, "talon-memory-rooms")[0].find('[data-key="other"]').text()).toContain("no data")
		expect(byId(wrapper, "talon-memory-growth")).toHaveLength(1)
		const rows = byId(wrapper, "talon-memory-row")
		expect(rows).toHaveLength(2)
		expect(rows[1].text()).toContain("Hidden: testing")
		expect(rows[1].text()).toContain("Durable")
		expect(api.listDrawers).toHaveBeenCalledWith(
			"ACME",
			expect.objectContaining({ limit: 50, cursor: null }),
			expect.anything()
		)
	})

	it("asks for nothing and says so for a role the routes don't serve", async () => {
		signInAs(AuthUserRole.CustomerUser)
		const wrapper = render()
		await settle()
		expect(byId(wrapper, "talon-memory-not-for-role")).toHaveLength(1)
		expect(api.getStats).not.toHaveBeenCalled()
		expect(getCustomers).not.toHaveBeenCalled()
	})

	it("asks to choose when there are several customers", async () => {
		getCustomers.mockReturnValue(
			ok({
				customers: [
					{ customer_code: "ACME", customer_name: "Acme" },
					{ customer_code: "GLOBEX", customer_name: "Globex" }
				]
			})
		)
		const wrapper = render()
		await settle()
		expect(byId(wrapper, "talon-memory-choose")[0].text()).toContain("Choose a customer")
		expect(api.getStats).not.toHaveBeenCalled()
	})

	it("an old Talon gets the upgrade notice and no list", async () => {
		api.getStats.mockImplementation(() => refusal(404, { detail: OLD_TALON_MEMORY_TEXT, code: "unsupported" }))
		const wrapper = render()
		await settle()
		const problem = byId(wrapper, "talon-memory-problem")[0]
		expect(problem.attributes("data-kind")).toBe("unsupported")
		expect(problem.text()).toContain(OLD_TALON_MEMORY_TEXT)
		expect(byId(wrapper, "talon-memory-drawers")).toHaveLength(0)
	})

	it("talon v2 turned off meanwhile says so", async () => {
		api.getStats.mockImplementation(() => refusal(404, { detail: "Not Found" }))
		const wrapper = render()
		await settle()
		const problem = byId(wrapper, "talon-memory-problem")[0]
		expect(problem.attributes("data-kind")).toBe("v2_off")
		expect(problem.text()).toContain(V2_OFF_TEXT)
	})

	it("a failure shows CoPilot's text and retries", async () => {
		api.getStats.mockImplementationOnce(() =>
			refusal(504, { detail: "Talon did not answer within 8 s", code: "unavailable" })
		)
		const wrapper = render()
		await settle()
		expect(byId(wrapper, "talon-memory-problem")[0].text()).toContain("Talon did not answer within 8 s (HTTP 504)")
		await byId(wrapper, "talon-memory-retry")[0].trigger("click")
		await settle()
		expect(api.getStats).toHaveBeenCalledTimes(2)
		expect(byId(wrapper, "talon-memory-total")[0].text()).toContain("42")
	})

	it("an empty memory says so", async () => {
		api.listDrawers.mockImplementation(() => ok({ success: true, items: [], next_cursor: null }))
		const wrapper = render()
		await settle()
		expect(byId(wrapper, "talon-memory-drawers-empty")[0].text()).toContain("no memories for this customer yet")
	})

	it("a breakdown row filters the list", async () => {
		const wrapper = render()
		await settle()
		await wrapper.get('[data-testid="talon-memory-sources"] [data-key="review_one_off"] button').trigger("click")
		await settle()
		expect(api.listDrawers).toHaveBeenLastCalledWith(
			"ACME",
			expect.objectContaining({ source: "review_one_off" }),
			expect.anything()
		)
	})

	it("the search waits for the typing to stop, and goes as q", async () => {
		const wrapper = render()
		await settle()
		api.listDrawers.mockClear()
		const input = byId(wrapper, "talon-memory-search")[0].find("input")
		await input.setValue("back")
		await input.setValue("backups on srv")
		await new Promise(resolve => setTimeout(resolve, SEARCH_DEBOUNCE_MS / 2))
		expect(api.listDrawers).not.toHaveBeenCalled()
		await new Promise(resolve => setTimeout(resolve, SEARCH_DEBOUNCE_MS))
		await settle()
		expect(api.listDrawers).toHaveBeenCalledTimes(1)
		expect(api.listDrawers.mock.calls[0][1]).toMatchObject({ q: "backups on srv", cursor: null })
		expect(byId(wrapper, "talon-memory-search-note")).toHaveLength(1)
	})

	it("load more asks with Talon's cursor and appends", async () => {
		api.listDrawers
			.mockImplementationOnce(() => ok({ success: true, items: [item()], next_cursor: "c1" }))
			.mockImplementationOnce(() => ok({ success: true, items: [item(DURABLE)], next_cursor: null }))
		const wrapper = render()
		await settle()
		await byId(wrapper, "talon-memory-more")[0].trigger("click")
		await settle()
		expect(api.listDrawers.mock.calls[1][1]).toMatchObject({ cursor: "c1" })
		expect(byId(wrapper, "talon-memory-row")).toHaveLength(2)
		expect(byId(wrapper, "talon-memory-more")).toHaveLength(0)
	})

	it("an id CoPilot can't open is listed without a way to open it", async () => {
		api.listDrawers.mockImplementation(() =>
			ok({ success: true, items: [item("drawer..odd", { openable: false })], next_cursor: null })
		)
		const wrapper = render()
		await settle()
		expect(byId(wrapper, "talon-memory-row")).toHaveLength(1)
		expect(byId(wrapper, "talon-memory-open")).toHaveLength(0)
	})
})

describe("a memory's detail", () => {
	async function opened(detail = drawer()) {
		api.getDrawer.mockImplementation(() => ok(detail))
		const wrapper = render()
		await settle()
		await byId(wrapper, "talon-memory-open")[0].trigger("click")
		await settle()
		return wrapper
	}

	it("renders the markdown through Markdown with images off, never as HTML", async () => {
		const wrapper = await opened()
		expect(api.getDrawer).toHaveBeenCalledWith("ACME", ONE_OFF, expect.anything())
		const markdown = byId(wrapper, "talon-memory-detail-content")[0]
		expect(markdown.attributes("data-no-images")).toBe("true")
		expect(markdown.text()).toContain('<img src=x onerror="alert(1)">')
		expect(wrapper.find("img").exists()).toBe(false)
	})

	it("links the investigation's job page and the alert", async () => {
		const wrapper = await opened()
		expect(JSON.parse(byId(wrapper, "talon-memory-detail-job")[0].attributes("data-to") ?? "null")).toEqual({
			name: "AiAnalystJob",
			params: { id: "copilot-inv-1-1760601600000" }
		})
		expect(JSON.parse(byId(wrapper, "talon-memory-detail-alert")[0].attributes("data-to") ?? "null")).toEqual({
			name: "IncidentManagement-Alert",
			params: { id: "7" }
		})
	})

	it("says why a memory is hidden, and that testing never lowers severity", async () => {
		const wrapper = await opened(
			drawer({ testing_hidden: true, visible_to_investigations: false, why_hidden: "Filed during a lab test" })
		)
		const hidden = byId(wrapper, "talon-memory-detail-hidden")[0]
		expect(hidden.text()).toContain("Filed during a lab test")
		expect(hidden.text()).toContain("never a reason to lower")
	})

	it("offers no Forget for what may not be forgotten, and says why", async () => {
		const wrapper = await opened(
			drawer({
				source: "investigation",
				forgettable: false,
				why_not_forgettable: "An investigation's own record"
			})
		)
		expect(byId(wrapper, "talon-memory-forget")).toHaveLength(0)
		expect(byId(wrapper, "talon-memory-not-forgettable")[0].text()).toContain("An investigation's own record")
	})

	it("forgets only after the confirm, then drops the row and re-reads the stats", async () => {
		api.forgetDrawer.mockImplementation(() => ok({ success: true, drawer_id: ONE_OFF }))
		const wrapper = await opened()
		await byId(wrapper, "talon-memory-forget")[0].trigger("click")
		expect(api.forgetDrawer).not.toHaveBeenCalled()
		await byId(wrapper, "talon-memory-forget-cancel")[0].trigger("click")
		expect(api.forgetDrawer).not.toHaveBeenCalled()
		await byId(wrapper, "talon-memory-forget")[0].trigger("click")
		await byId(wrapper, "talon-memory-forget-confirm-button")[0].trigger("click")
		await settle()
		expect(api.forgetDrawer).toHaveBeenCalledWith("ACME", ONE_OFF)
		expect(byId(wrapper, "talon-memory-row").map(r => r.attributes("data-drawer"))).toEqual([DURABLE])
		expect(api.getStats).toHaveBeenCalledTimes(2)
		expect(byId(wrapper, "drawer-stub")).toHaveLength(0)
	})

	it("a refused forget shows Talon's reason and keeps the memory", async () => {
		api.forgetDrawer.mockImplementation(() =>
			refusal(409, { detail: "A durable lesson can't be forgotten", code: "refused" })
		)
		const wrapper = await opened()
		await byId(wrapper, "talon-memory-forget")[0].trigger("click")
		await byId(wrapper, "talon-memory-forget-confirm-button")[0].trigger("click")
		await settle()
		expect(byId(wrapper, "talon-memory-forget-error")[0].text()).toBe("A durable lesson can't be forgotten")
		expect(byId(wrapper, "talon-memory-row")).toHaveLength(2)
	})

	it("an unknown memory says so", async () => {
		api.getDrawer.mockImplementation(() => refusal(404, { detail: "Talon has no such memory", code: "not_found" }))
		const wrapper = render()
		await settle()
		await byId(wrapper, "talon-memory-open")[0].trigger("click")
		await settle()
		expect(byId(wrapper, "talon-memory-problem")[0].text()).toContain("Talon has no such memory")
	})
})

describe("assets", () => {
	it("lists the assets and shows one's timeline, oldest first", async () => {
		const wrapper = render()
		await settle()
		await wrapper.get('[data-testid="talon-memory-view-assets"] input').setValue(true)
		await settle()
		expect(api.listAssets).toHaveBeenCalledWith("ACME", { q: null, limit: 100 }, expect.anything())
		await byId(wrapper, "talon-memory-asset")[0].trigger("click")
		await settle()
		expect(api.getAssetTimeline).toHaveBeenCalledWith("ACME", "SRV-01", expect.anything())
		const facts = byId(wrapper, "talon-memory-fact")
		expect(facts.map(f => f.text())).toEqual([expect.stringContaining("owned by"), expect.stringContaining("runs")])
		expect(facts[0].text()).toContain("no longer true")
	})
})

describe("my chat memory", () => {
	it("lists the caller's own and forgets after a confirm, naming no user", async () => {
		api.forgetMyChatMemory.mockImplementation(() => ok({ success: true, drawer_id: "drawer_chat_1" }))
		const wrapper = render()
		await settle()
		await wrapper.find('[data-open="chat"]').trigger("click")
		await settle()
		expect(api.listMyChatMemory).toHaveBeenCalledWith(expect.anything())
		expect(byId(wrapper, "talon-memory-chat-item")[0].text()).toContain("Prefers UTC")
		await byId(wrapper, "talon-memory-chat-forget")[0].trigger("click")
		expect(api.forgetMyChatMemory).not.toHaveBeenCalled()
		await byId(wrapper, "talon-memory-chat-confirm-button")[0].trigger("click")
		await settle()
		expect(api.forgetMyChatMemory).toHaveBeenCalledWith("drawer_chat_1")
		expect(byId(wrapper, "talon-memory-chat-item")).toHaveLength(0)
		expect(byId(wrapper, "talon-memory-chat-empty")).toHaveLength(1)
	})

	it("an old Talon gets the notice here too", async () => {
		api.listMyChatMemory.mockImplementation(() =>
			refusal(404, { detail: OLD_TALON_MEMORY_TEXT, code: "unsupported" })
		)
		const wrapper = render()
		await settle()
		const chat = wrapper.find('[data-pane="chat"]')
		expect(chat.find('[data-testid="talon-memory-problem"]').attributes("data-kind")).toBe("unsupported")
	})
})
