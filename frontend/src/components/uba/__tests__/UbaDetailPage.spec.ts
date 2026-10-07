import type { RouteRecordRaw } from "vue-router"
import type { UbaDrawerMeta } from "../ui/UbaDrawerHeader.vue"
import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { describe, expect, it, vi } from "vitest"
import { defineComponent, h, ref } from "vue"
import { createMemoryHistory, createRouter } from "vue-router"
import { ubaRoutes } from "@/router/routes/uba"
import UbaDetailPage from "../UbaDetailPage.vue"

const ALERT_META: UbaDrawerMeta = {
	kind: "UBA alert",
	icon: "carbon:warning-alt",
	title: "CONTOSO\\Administrator",
	risk: 107
}
const ENTITY_KEY = "windows-demo\\jdoe"

const copy = vi.hoisted(() => vi.fn())
vi.mock("@vueuse/core", async importOriginal => ({
	...(await importOriginal<typeof import("@vueuse/core")>()),
	useClipboard: () => ({ copy, copied: ref(false) })
}))

// The bodies are the drawers' own components, covered in ui.spec.ts: here they only report their
// header and ask to open the other kind, which is what the page wires.
vi.mock("../UbaAlertDetail.vue", () => ({
	default: defineComponent({
		props: { customerCode: String, alertId: String },
		emits: ["meta", "openEntity"],
		setup(props, { emit }) {
			emit("meta", ALERT_META)
			return () =>
				h(
					"button",
					{ "data-testid": "stub-open-entity", onClick: () => emit("openEntity", ENTITY_KEY) },
					`alert ${props.alertId}`
				)
		}
	})
}))
vi.mock("../UbaEntityDetail.vue", () => ({
	default: defineComponent({
		props: { customerCode: String, entityKey: String },
		emits: ["meta", "openAlert"],
		setup(props, { emit }) {
			return () =>
				h(
					"button",
					{ "data-testid": "stub-open-alert", onClick: () => emit("openAlert", "a-2") },
					`entity ${props.entityKey}`
				)
		}
	})
}))

function makeRouter() {
	return createRouter({
		history: createMemoryHistory(),
		routes: [
			...(ubaRoutes.map(r => (r.redirect ? r : { ...r, component: { render: () => null } })) as RouteRecordRaw[]),
			{ path: "/", component: { render: () => null } }
		]
	})
}

async function render(kind: "alert" | "entity", id: string) {
	const router = makeRouter()
	await router.push(
		kind === "alert"
			? `/uba/ACME/alerts/${id}`
			: { name: "UbaEntity", params: { customerCode: "ACME", entityKey: id } }
	)
	const wrapper = mount(
		defineComponent({
			setup: () => () =>
				h(NMessageProvider, null, { default: () => h(UbaDetailPage, { customerCode: "ACME", kind, id }) })
		}),
		{ global: { plugins: [router] } }
	)
	await flushPromises()
	return { wrapper, router }
}

describe("ubaDetailPage", () => {
	it("shows the alert's header from its body, and the customer", async () => {
		const { wrapper } = await render("alert", "a-1")
		expect(wrapper.get("[data-testid=uba-detail-customer]").text()).toBe("ACME")
		expect(wrapper.get("[data-testid=uba-drawer-title]").text()).toBe("CONTOSO\\Administrator")
		expect(wrapper.get("[data-testid=uba-drawer-kind]").text()).toBe("UBA alert")
		expect(wrapper.text()).toContain("alert a-1")
	})

	it("links the customer's view and copies a link to the page", async () => {
		copy.mockReset().mockResolvedValue(undefined)
		const { wrapper } = await render("alert", "a-1")
		expect(wrapper.get("[data-testid=uba-detail-customer]").attributes("href")).toBe("/uba?customer=ACME")
		await wrapper.get("[data-testid=uba-detail-copy-link]").trigger("click")
		await flushPromises()
		expect(copy).toHaveBeenCalledWith(`${window.location.protocol}//${window.location.host}/uba/ACME/alerts/a-1`)
	})

	it("opens the entity's page from an alert, with the key encoded in the path", async () => {
		const { wrapper, router } = await render("alert", "a-1")
		await wrapper.get("[data-testid=stub-open-entity]").trigger("click")
		await flushPromises()
		expect(router.currentRoute.value.name).toBe("UbaEntity")
		expect(router.currentRoute.value.params).toEqual({ customerCode: "ACME", entityKey: ENTITY_KEY })
		expect(router.currentRoute.value.path).toBe("/uba/ACME/entities/windows-demo%5Cjdoe")
	})

	it("opens an alert's page from an entity", async () => {
		const { wrapper, router } = await render("entity", ENTITY_KEY)
		expect(wrapper.get("[data-testid=uba-drawer-kind]").text()).toBe("Entity")
		await wrapper.get("[data-testid=stub-open-alert]").trigger("click")
		await flushPromises()
		expect(router.currentRoute.value.path).toBe("/uba/ACME/alerts/a-2")
	})

	it("goes back to User Behavior on the customer and the matching tab when there is no history", async () => {
		const { wrapper, router } = await render("entity", ENTITY_KEY)
		await wrapper.findAll("button").find(b => b.text() === "User Behavior")?.trigger("click")
		await flushPromises()
		expect(router.currentRoute.value.name).toBe("Uba")
		expect(router.currentRoute.value.query).toEqual({ customer: "ACME", tab: "entities" })
	})
})

describe("uba routes", () => {
	it("send every prefix of a detail page's path to the matching view of /uba", async () => {
		const router = makeRouter()
		await router.push("/uba/ACME")
		expect(router.currentRoute.value.name).toBe("Uba")
		expect(router.currentRoute.value.query).toEqual({ customer: "ACME" })
		await router.push("/uba/ACME/alerts")
		expect(router.currentRoute.value.query).toEqual({ customer: "ACME", tab: "alerts" })
		await router.push("/uba/ACME/entities")
		expect(router.currentRoute.value.query).toEqual({ customer: "ACME", tab: "entities" })
	})

	it("round-trip entity keys with backslashes, colons and at signs", () => {
		const router = makeRouter()
		for (const entityKey of [
			"windows-demo\\jdoe",
			"upn:jane@contoso.com",
			"eb936d60-d268-49bf-9149-1c8bcdf05ef3"
		]) {
			const href = router.resolve({ name: "UbaEntity", params: { customerCode: "ACME", entityKey } }).href
			expect(router.resolve(href).params.entityKey).toBe(entityKey)
		}
	})
})
