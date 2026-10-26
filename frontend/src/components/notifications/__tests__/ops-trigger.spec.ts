import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider, NSelect } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import CustomerAiNotificationRouteForm from "@/components/customers/aiNotifications/CustomerAiNotificationRoutes/CustomerAiNotificationRouteForm.vue"
import NotificationTemplateForm from "@/components/notifications/NotificationTemplateForm.vue"
import { variablesForTrigger } from "@/components/notifications/templateVariables"
import { INTERNAL_TRIGGERS, isInternalTrigger } from "@/types/notifications"

/**
 * Talon's ops findings trigger (`talon_ops_finding`, talon-analyst D96) is internal only: the route
 * form offers it on internal routes and never on a customer's; templates can be scoped to it and
 * list its `context.ops_finding` variables.
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
		defineComponent({
			setup: () => () => h(NMessageProvider, null, { default: () => h(component as never, props) })
		})
	)
}

function selectOffering(wrapper: ReturnType<typeof mount>, value: string) {
	const select = wrapper
		.findAllComponents(NSelect)
		.find(candidate =>
			((candidate.props("options") as { value: string }[]) ?? []).some(option => option.value === value)
		)
	if (!select) throw new Error(`no select offers ${value}`)
	return select
}

function values(select: { props: (name: string) => unknown }) {
	return (select.props("options") as { value: string }[]).map(option => option.value)
}

beforeEach(() => setActivePinia(createPinia()))

describe("route form", () => {
	it("offers the ops trigger on internal routes", async () => {
		const wrapper = mountInProvider(CustomerAiNotificationRouteForm, { editingRoute: null, scope: "internal" })
		await flushPromises()
		const trigger = selectOffering(wrapper, "alert_assigned")
		const options = trigger.props("options") as { value: string; label: string }[]
		expect(options.find(o => o.value === "talon_ops_finding")?.label).toBe("Talon flags something in the stack")
	})

	it("never offers it on a customer's route", async () => {
		const wrapper = mountInProvider(CustomerAiNotificationRouteForm, {
			editingRoute: null,
			scope: "customer",
			customerCode: "ACME"
		})
		await flushPromises()
		expect(values(selectOffering(wrapper, "alert_created"))).not.toContain("talon_ops_finding")
	})
})

describe("the trigger", () => {
	it("is internal", () => {
		expect(INTERNAL_TRIGGERS).toContain("talon_ops_finding")
		expect(isInternalTrigger("talon_ops_finding")).toBe(true)
	})

	it("lists the ops variables, the model's text marked untrusted", () => {
		const names = variablesForTrigger("talon_ops_finding").map(v => v.name)
		expect(names).toEqual(
			expect.arrayContaining([
				"context.ops_finding.why",
				"context.ops_finding.recommendation",
				"context.ops_finding_json"
			])
		)
		expect(names).not.toContain("context.asset_name")
		const why = variablesForTrigger("talon_ops_finding").find(v => v.name === "context.ops_finding.why")
		expect(why?.description).toContain("untrusted")
	})
})

describe("template form", () => {
	it("can scope a template to the ops trigger", async () => {
		const wrapper = mountInProvider(NotificationTemplateForm, { editingTemplate: null })
		await flushPromises()
		const trigger = selectOffering(wrapper, "alert_assigned")
		const labels = Object.fromEntries(
			(trigger.props("options") as { value: string; label: string }[]).map(o => [o.value, o.label])
		)
		expect(labels.talon_ops_finding).toBe("Talon ops finding")
	})
})
