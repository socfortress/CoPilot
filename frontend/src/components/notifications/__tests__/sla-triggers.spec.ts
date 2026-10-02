import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider, NSelect } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import CustomerAiNotificationRouteForm from "@/components/customers/aiNotifications/CustomerAiNotificationRoutes/CustomerAiNotificationRouteForm.vue"
import NotificationTemplateForm from "@/components/notifications/NotificationTemplateForm.vue"

/**
 * The SLA notification triggers (#1187) are internal: a SOC running late is never the
 * customer's notification. The route form offers them on internal routes only — where an
 * email can go to whoever the item is assigned to — and templates can be scoped to them.
 */

const RESEND = {
	key: "resend",
	display_name: "Email (Resend)",
	supports_recipient_modes: ["static", "assignee"],
	supports_internal_scope: true,
	config_schema: {}
}

// Every endpoint the forms touch answers an empty, successful payload; the catalog
// answers one email channel.
vi.mock("@/api", () => {
	const ok = (data: Record<string, unknown> = {}) => Promise.resolve({ data: { success: true, ...data } })
	const endpoint = (name: string) => () =>
		name === "getChannels"
			? ok({ channels: [RESEND] })
			: ok({ templates: [], integrations: [], customers: [], notifications: [], apps: [] })
	const anyEndpoint = () => new Proxy({}, { get: (_, name: string) => endpoint(name) })
	return {
		default: new Proxy(
			{},
			{
				get: (_, area: string) =>
					area === "incidentManagement" ? { notification: anyEndpoint() } : anyEndpoint()
			}
		)
	}
})

function mountInProvider(component: unknown, props: Record<string, unknown>) {
	return mount(
		defineComponent({ setup: () => () => h(NMessageProvider, null, { default: () => h(component as never, props) }) })
	)
}

function selectOffering(wrapper: ReturnType<typeof mount>, value: string) {
	const select = wrapper
		.findAllComponents(NSelect)
		.find(candidate => ((candidate.props("options") as { value: string }[]) ?? []).some(option => option.value === value))
	if (!select) throw new Error(`no select offers ${value}`)
	return select
}

function values(select: { props: (name: string) => unknown }) {
	return (select.props("options") as { value: string }[]).map(option => option.value)
}

beforeEach(() => setActivePinia(createPinia()))

describe("route form", () => {
	it("offers the SLA triggers on internal routes", async () => {
		const wrapper = mountInProvider(CustomerAiNotificationRouteForm, { editingRoute: null, scope: "internal" })
		await flushPromises()
		const trigger = selectOffering(wrapper, "alert_assigned")
		expect(values(trigger)).toEqual(expect.arrayContaining(["sla_at_risk", "sla_breached"]))
		expect((trigger.props("options") as { value: string; label: string }[]).find(o => o.value === "sla_breached")?.label).toBe(
			"An alert or case SLA is breached"
		)
	})

	it("never offers them on a customer's route", async () => {
		const wrapper = mountInProvider(CustomerAiNotificationRouteForm, {
			editingRoute: null,
			scope: "customer",
			customerCode: "ACME"
		})
		await flushPromises()
		const trigger = selectOffering(wrapper, "alert_created")
		expect(values(trigger)).not.toContain("sla_at_risk")
		expect(values(trigger)).not.toContain("sla_breached")
	})

	it("lets an SLA email go to whoever the item is assigned to", async () => {
		const wrapper = mountInProvider(CustomerAiNotificationRouteForm, { editingRoute: null, scope: "internal" })
		await flushPromises()
		selectOffering(wrapper, "alert_assigned").vm.$emit("update:value", "sla_breached")
		await flushPromises()
		const recipients = selectOffering(wrapper, "assignee")
		expect(values(recipients)).toEqual(["static", "assignee"])
	})
})

describe("template form", () => {
	it("can scope a template to either SLA trigger", async () => {
		const wrapper = mountInProvider(NotificationTemplateForm, { editingTemplate: null })
		await flushPromises()
		const trigger = selectOffering(wrapper, "alert_assigned")
		const labels = Object.fromEntries((trigger.props("options") as { value: string; label: string }[]).map(o => [o.value, o.label]))
		expect(labels.sla_at_risk).toBe("SLA at risk")
		expect(labels.sla_breached).toBe("SLA breached")
	})
})
