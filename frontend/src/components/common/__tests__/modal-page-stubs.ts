/**
 * Stubs for "open the page" button specs, kept free of app imports on purpose: they
 * are loaded from `vi.mock` factories (naive-ui, @/api), and importing anything that
 * imports naive-ui from there would deadlock the mock.
 *
 * - `stubOverlays(naive)` replaces NModal / NDrawer / NDrawerContent with stubs that
 *   render their slots inline and expose `show` as `data-show`, so a spec can open an
 *   overlay, read its header and see it close — no teleport, no transitions.
 * - `pendingApi(overrides)` is an Api whose every call stays pending unless overridden.
 */
import { defineComponent, h } from "vue"

const OverlayStub = defineComponent({
	name: "OverlayStub",
	props: { show: { type: Boolean, default: false } },
	emits: ["update:show"],
	setup(props, { slots }) {
		return () =>
			// A real overlay teleports to <body>: a click inside it never reaches the card that
			// owns it. Stop it here, or a card that opens on click would reopen at once.
			h("div", { "data-testid": "overlay-stub", "data-show": String(props.show), onClick: (e: Event) => e.stopPropagation() }, [
				slots["header-extra"]?.(),
				slots.header?.(),
				slots.default?.()
			])
	}
})

const quiet = { success: () => {}, error: () => {}, warning: () => {}, info: () => {}, loading: () => {} }

/** Overlays rendered inline, and the message / dialog APIs that need a provider made inert. */
export function stubOverlays<T extends Record<string, unknown>>(naive: T): T {
	return {
		...naive,
		NModal: OverlayStub,
		NDrawer: OverlayStub,
		NDrawerContent: OverlayStub,
		useMessage: () => quiet,
		useDialog: () => quiet
	}
}

export function pendingApi(overrides: Record<string, Record<string, unknown>> = {}) {
	// Any path is reachable and callable (Api.wazuh.mitre.getMitreGroups(...)); every call
	// returns a promise that never settles, so a component just stays "loading".
	const anything = (): unknown =>
		new Proxy(() => new Promise(() => {}), {
			get: (_target, key) => (key === "then" ? undefined : anything())
		})
	return new Proxy(overrides, {
		get: (target, area: string) => target[area] ?? anything()
	})
}
