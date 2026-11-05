import type { NotificationRoute } from "@/types/notifications"
import { flushPromises, mount } from "@vue/test-utils"
import { NButton, NInput, NMessageProvider, NSelect } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import CustomerAiNotificationRouteForm from "../CustomerAiNotificationRouteForm.vue"
import { buildGenericChannelConfig } from "../genericChannelConfig"

/**
 * Teams has no block of its own in the route form: ChannelConfigFields renders it from the schema
 * its provider advertises, and its config has to be built the same way. It used to fall into the
 * Shuffle branch, which dropped the URL and sent app_id/app_name, refused by extra="forbid" (#1336).
 */

const WEBHOOK = "https://prod.westus.logic.azure.com/workflows/abc/triggers/manual/paths/invoke"

const TEAMS = {
	key: "teams",
	display_name: "Microsoft Teams",
	supports_recipient_modes: ["static"],
	supports_internal_scope: true,
	secret_fields: ["webhook_url"],
	template_formats: ["text"],
	config_schema: {
		properties: {
			webhook_url: { anyOf: [{ type: "string" }, { type: "null" }], default: null, title: "Webhook Url" }
		}
	}
}

const SHUFFLE = { ...TEAMS, key: "shuffle", display_name: "Shuffle", supports_internal_scope: false, config_schema: {} }

const api = vi.hoisted(() => ({
	createRoute: vi.fn(),
	updateRoute: vi.fn(),
	getChannels: vi.fn()
}))

const messages = vi.hoisted(() => ({ error: vi.fn() }))

vi.mock("naive-ui", async importOriginal => ({
	...(await importOriginal<typeof import("naive-ui")>()),
	useMessage: () => ({ error: messages.error, success: vi.fn(), warning: vi.fn() })
}))

vi.mock("@/api", () => {
	const ok = () =>
		Promise.resolve({ data: { success: true, templates: [], integrations: [], notifications: [], apps: [] } })
	const anyEndpoint = (known: Record<string, unknown> = {}) =>
		new Proxy(known, { get: (target, name: string) => target[name] ?? ok })
	return {
		default: new Proxy(
			{},
			{
				get: (_, area: string) =>
					area === "notifications"
						? anyEndpoint(api)
						: area === "incidentManagement"
							? { notification: anyEndpoint() }
							: anyEndpoint()
			}
		)
	}
})

async function mountForm(editingRoute: Partial<NotificationRoute> | null = null) {
	const wrapper = mount(
		defineComponent({
			setup: () => () =>
				h(NMessageProvider, null, {
					default: () => h(CustomerAiNotificationRouteForm, { editingRoute, customerCode: "acme" } as never)
				})
		})
	)
	await flushPromises()
	return wrapper
}

function selectOffering(wrapper: Awaited<ReturnType<typeof mountForm>>, value: string) {
	const select = wrapper
		.findAllComponents(NSelect)
		.find(candidate =>
			((candidate.props("options") as { value: string }[]) ?? []).some(option => option.value === value)
		)
	if (!select) throw new Error(`no select offers ${value}`)
	return select
}

function typeInto(wrapper: Awaited<ReturnType<typeof mountForm>>, prop: string, value: string) {
	const input = wrapper.findAllComponents(NInput).find(candidate => candidate.props(prop as never))
	if (!input) throw new Error(`no input with ${prop}`)
	input.vm.$emit("update:value", value)
}

async function save(wrapper: Awaited<ReturnType<typeof mountForm>>, label: string) {
	const button = wrapper.findAllComponents(NButton).find(b => b.text() === label)
	if (!button) throw new Error(`no button ${label}`)
	await button.trigger("click")
	await flushPromises()
}

const teamsRoute: Partial<NotificationRoute> = {
	id: 7,
	name: "SOC Teams",
	trigger: "alert_created",
	channel: "teams",
	min_severity: "Medium",
	enabled: true,
	scope: "customer",
	recipient_mode: "static",
	destination: null,
	shuffle_integration_id: null,
	config: { webhook_url: WEBHOOK }
}

beforeEach(() => {
	setActivePinia(createPinia())
	vi.clearAllMocks()
	api.getChannels.mockResolvedValue({ data: { success: true, channels: [SHUFFLE, TEAMS] } })
	api.createRoute.mockResolvedValue({ data: { success: true } })
	api.updateRoute.mockResolvedValue({ data: { success: true } })
})

describe("a Teams route in the form", () => {
	it("creates the route with the URL typed in the generic field and nothing of Shuffle's", async () => {
		const wrapper = await mountForm()
		typeInto(wrapper, "maxlength", "SOC Teams")
		const channel = selectOffering(wrapper, "teams")
		channel.vm.$emit("update:value", "teams")
		await flushPromises()

		typeInto(wrapper, "clearable", `  ${WEBHOOK} `)
		await save(wrapper, "Create route")

		expect(api.createRoute).toHaveBeenCalledOnce()
		const [code, payload] = api.createRoute.mock.calls[0]
		expect(code).toBe("acme")
		expect(payload).toMatchObject({ channel: "teams", destination: null, shuffle_integration_id: null })
		expect(payload.config).toEqual({ webhook_url: WEBHOOK })
	})

	it("keeps the stored URL when another field is edited", async () => {
		const wrapper = await mountForm(teamsRoute)
		await save(wrapper, "Save changes")

		expect(api.updateRoute).toHaveBeenCalledOnce()
		expect(api.updateRoute.mock.calls[0][2].config).toEqual({ webhook_url: WEBHOOK })
	})

	it("refuses a cleared URL: a PATCH without one saves a route that cannot deliver", async () => {
		const wrapper = await mountForm(teamsRoute)
		typeInto(wrapper, "clearable", "   ")
		await flushPromises()
		await save(wrapper, "Save changes")

		expect(api.updateRoute).not.toHaveBeenCalled()
	})

	it("saves nothing without the catalog: an empty config would erase the stored URL", async () => {
		api.getChannels.mockRejectedValue(new Error("no catalog"))
		const wrapper = await mountForm(teamsRoute)
		await save(wrapper, "Save changes")

		expect(api.updateRoute).not.toHaveBeenCalled()
		expect(messages.error).toHaveBeenCalledOnce()
	})

	it("leaves Shuffle's config alone", async () => {
		const wrapper = await mountForm({
			...teamsRoute,
			channel: "shuffle",
			destination: "#soc",
			shuffle_integration_id: 3,
			config: { app_id: "app-1", app_name: "Slack" }
		})
		await save(wrapper, "Save changes")

		expect(api.updateRoute).toHaveBeenCalledOnce()
		const payload = api.updateRoute.mock.calls[0][2]
		expect(payload).toMatchObject({ destination: "#soc", shuffle_integration_id: 3 })
		expect(payload.config).toEqual({ app_id: "app-1", app_name: "Slack" })
	})
})

describe("the channel hint", () => {
	const SHUFFLE_HINT = "Shuffle proxies to 3,000+ integrations"

	it.each([
		["teams", "Power Automate Workflows webhook"],
		["resend", "Sends email directly through Resend"]
	])("doesn't describe %s as Shuffle", async (channel, hint) => {
		const wrapper = await mountForm({ ...teamsRoute, channel: channel as NotificationRoute["channel"] })

		expect(wrapper.text()).toContain(hint)
		expect(wrapper.text()).not.toContain(SHUFFLE_HINT)
	})

	it("still describes Shuffle", async () => {
		const wrapper = await mountForm({ ...teamsRoute, channel: "shuffle" })

		expect(wrapper.text()).toContain(SHUFFLE_HINT)
	})

	it("says nothing of a channel it doesn't know", async () => {
		const wrapper = await mountForm({ ...teamsRoute, channel: "pager" as NotificationRoute["channel"] })

		expect(wrapper.text()).not.toContain(SHUFFLE_HINT)
	})
})

describe("buildGenericChannelConfig", () => {
	const descriptor = {
		...TEAMS,
		config_schema: {
			properties: { webhook_url: {}, retries: {}, verbose: {}, cc: {}, optional: {} }
		}
	} as never

	it("keeps only what the schema names and leaves empty fields to the provider", () => {
		expect(
			buildGenericChannelConfig(descriptor, {
				webhook_url: " https://hook ",
				retries: 0,
				verbose: false,
				cc: ["a@b.c", " ", ""],
				optional: "  ",
				app_id: "left over from Shuffle",
				app_name: null
			})
		).toEqual({ webhook_url: "https://hook", retries: 0, verbose: false, cc: ["a@b.c"] })
	})

	it("is empty for a schema with no properties", () => {
		expect(buildGenericChannelConfig({ ...TEAMS, config_schema: {} } as never, { webhook_url: "x" })).toEqual({})
	})
})
