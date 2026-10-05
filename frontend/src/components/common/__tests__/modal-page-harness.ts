/**
 * Test harness for "open the page" buttons in entity modals and drawers.
 *
 * - `appRouter()` is the app's real route table with every page swapped for a blank
 *   component, so a spec checks the link against the routes users actually hit
 *   without loading a single view.
 * - The overlay and Api stubs live in `modal-page-stubs.ts`, which `vi.mock` factories
 *   can import without pulling naive-ui in.
 */
import type { Component } from "vue"
import type { RouteRecordRaw } from "vue-router"
import { flushPromises, mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { defineComponent } from "vue"
import { createMemoryHistory, createRouter } from "vue-router"
import { routes } from "@/router/routes"

const blank = defineComponent({ name: "BlankPage", render: () => null })

function blankOut(records: RouteRecordRaw[]): RouteRecordRaw[] {
	return records.map(record => {
		const copy = { ...record } as RouteRecordRaw & { component?: unknown; components?: unknown }
		if ("component" in copy && copy.component) copy.component = blank
		if ("components" in copy && copy.components) copy.components = { default: blank }
		if (record.children) copy.children = blankOut(record.children)
		return copy as RouteRecordRaw
	})
}

export function appRouter() {
	return createRouter({ history: createMemoryHistory(), routes: blankOut(routes) })
}

/** Mounts `component` with the app router and a fresh Pinia, stubbing heavy children. */
export async function mountWithRouter(component: Component, props: Record<string, unknown>, stubs: string[] = []) {
	setActivePinia(createPinia())
	const router = appRouter()
	await router.push("/")
	await router.isReady()
	const wrapper = mount(component as never, {
		props: props as never,
		global: {
			plugins: [router],
			stubs: Object.fromEntries(stubs.map(name => [name, true]))
		}
	})
	await flushPromises()
	return { wrapper, router }
}
