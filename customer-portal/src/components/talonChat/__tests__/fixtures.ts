import type { Component } from "vue"
import type { TalonChatThread, TalonChatUIMessage, TalonSocDraft } from "@/types/talonChat"
import { NMessageProvider } from "naive-ui"
import { defineComponent, h } from "vue"
import { createMemoryHistory, createRouter } from "vue-router"

export function thread(overrides: Partial<TalonChatThread> = {}): TalonChatThread {
	return {
		id: "th-1",
		title: "Scheduled task on HOST-A",
		customer_code: "ACME",
		context_alert_id: null,
		language: "en",
		status: "active",
		created_at: "2026-10-31T09:00:00Z",
		updated_at: "2026-10-31T09:05:00Z",
		archived_at: null,
		accessible: true,
		...overrides
	}
}

export function draft(overrides: Partial<TalonSocDraft> = {}): TalonSocDraft {
	return {
		id: "d-1",
		thread_id: "th-1",
		customer_code: "ACME",
		target: { kind: "alert", id: 4127 },
		question: "Was the scheduled task on HOST-A expected?",
		urgency: null,
		file_on: null,
		status: "pending",
		created_at: "2026-10-31T09:05:00Z",
		expires_at: "2026-11-01T09:05:00Z",
		claimed_at: null,
		copilot_ref: null,
		...overrides
	}
}

/** One completed turn as the read-back gives it. */
export function turn(run: string, prompt: string, parts: unknown[], metadata: Record<string, unknown> = {}): TalonChatUIMessage[] {
	return [
		{ id: `${run}-user`, role: "user", parts: [{ type: "text", text: prompt }], metadata: { created_at: "2026-10-31T09:01:00Z" } },
		{
			id: `${run}-assistant`,
			role: "assistant",
			parts,
			metadata: { created_at: "2026-10-31T09:02:00Z", status: "completed", ...metadata }
		}
	]
}

export function testRouter() {
	const Empty = defineComponent({ render: () => null })
	return createRouter({
		history: createMemoryHistory(),
		routes: [
			{ path: "/", component: Empty },
			{ path: "/talon", name: "TalonChat", component: Empty },
			{ path: "/alerts/:id", name: "AlertDetails", component: Empty }
		]
	})
}

/** `component` inside the message provider its toasts need. */
export function withProviders(component: Component, props: Record<string, unknown> = {}) {
	return defineComponent({
		setup: () => () => h(NMessageProvider, null, () => h(component, props))
	})
}
