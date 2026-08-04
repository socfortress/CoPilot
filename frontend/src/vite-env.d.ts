/// <reference types="vite/client" />

/**
 * Build-time overrides for the external entries in the user menu. Frozen into the bundle by Vite,
 * so on a prebuilt image the runtime layer below is the one that applies.
 */
interface ImportMetaEnv {
	/** Label of the documentation entry. Falls back to "Documentation". */
	readonly VITE_DOCUMENTATION_LABEL?: string
	/** URL the documentation entry opens. Falls back to the SOCFortress docs site. */
	readonly VITE_DOCUMENTATION_URL?: string
	/** Label of the support entry. Falls back to "Contact SOCFortress". */
	readonly VITE_CONTACT_LABEL?: string
	/** URL the support entry opens. Falls back to the SOCFortress contact page. */
	readonly VITE_CONTACT_URL?: string
}

/**
 * Runtime overrides, served by /config.js and regenerated from container environment variables on
 * every start by build/docker-entrypoint.d/91-copilot-runtime-config.sh. Each key is optional; an
 * absent one leaves the build-time value or the compiled-in default in place.
 */
interface CopilotRuntimeConfig {
	documentationLabel?: string
	documentationUrl?: string
	contactLabel?: string
	contactUrl?: string
}

interface Window {
	__COPILOT_CONFIG__?: CopilotRuntimeConfig
}

declare module "*.vue" {
	import type { DefineComponent } from "vue"

	const component: DefineComponent<Record<string, unknown>, Record<string, unknown>, any>
	export default component
}

declare module "*.svg" {
	import type { DefineComponent } from "vue"

	const component: DefineComponent
	export default component
}
