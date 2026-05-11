<template>
	<div ref="container" class="w-full" />
</template>

<script setup lang="ts">
// Vue wrapper around `<ShuffleMCP>` (a React component from
// `@shuffleio/shuffle-mcps`). We don't pull in a Vue/React interop
// library — for a single component the manual mount via
// react-dom/client is cleaner and avoids the abstraction tax. Vite
// already handles JSX through esbuild so no build config changes
// were needed.
//
// Lifecycle: createRoot in onMounted, unmount in onBeforeUnmount,
// re-render with `root.render(...)` on prop change so the embed
// reacts to live updates (e.g. when the parent swaps the auth token
// after picking a different Shuffle org).

// Side-effect import: overrides API_CONFIG.baseUrl to point at our
// same-origin proxy. Must come before any other `@shuffleio/shuffle-mcps`
// import so the override is in place when the package initialises.
import "@/composables/installShuffleApiBase"
import type { Root } from "react-dom/client"
// `@shuffleio/shuffle-mcps/dist/index.js` self-imports its CSS via a
// hash-suffixed filename (`./singul-GZKBHJNI.css`). The package's own
// `./singul.css` export entry points at `./dist/singul.css` which
// doesn't exist on disk — that's a package bug. We don't need to
// import the CSS here ourselves; importing `ShuffleMCP` pulls it in.
import { ShuffleMCP } from "@shuffleio/shuffle-mcps"
import { createElement } from "react"
import { createRoot } from "react-dom/client"
import { onBeforeUnmount, onMounted, ref, watch } from "vue"
import { fetchShuffleConnectorCredentials } from "@/composables/shuffleConnectorCredentials"

interface Props {
	authToken: string
	apiKey?: string
	apiBaseUrl?: string
	inline?: boolean
	layout?: "list" | "grid"
	gridColumns?: number
	placeholder?: string
	preventDefault?: boolean
	multiSelect?: boolean
	showCheckbox?: boolean
	initialFilterQuery?: string
	showSourceFilter?: boolean
}

const props = withDefaults(defineProps<Props>(), {
	apiKey: undefined,
	apiBaseUrl: undefined,
	inline: true,
	layout: "list",
	gridColumns: 3,
	placeholder: "Find an app…",
	preventDefault: false,
	multiSelect: false,
	showCheckbox: false,
	initialFilterQuery: undefined,
	showSourceFilter: true
})

const emit = defineEmits<{
	(e: "appSelected", payload: unknown): void
	(e: "selectionChange", payload: unknown): void
}>()

const container = ref<HTMLElement | null>(null)
let root: Root | null = null
const EMPTY_SELECTED_APPS: unknown[] = []

// Connector creds (URL + admin API key) read from CoPilot's `connectors`
// table. Without these, ShuffleMCP fetches private/authenticated apps
// unauthenticated and CORS-blocks against the default `shuffler.io`
// origin. Loaded lazily so the embed doesn't gate on the round-trip
// when the caller already passed explicit overrides.
const connectorApiKey = ref<string | null>(null)
const connectorBaseUrl = ref<string | null>(null)

function render() {
	if (!root) return
	// Drop undefined props so React doesn't override the package's
	// own defaults with our `undefined` (different semantics in TS vs
	// React's prop-default mechanism).
	const reactProps: Record<string, unknown> = {
		authToken: props.authToken,
		inline: props.inline,
		layout: props.layout,
		gridColumns: props.gridColumns,
		placeholder: props.placeholder,
		preventDefault: props.preventDefault,
		multiSelect: props.multiSelect,
		showCheckbox: props.showCheckbox,
		showSourceFilter: props.showSourceFilter,
		// The package currently defaults `selectedApps` to a fresh `[]`
		// inside the React component, then mirrors it into state from a
		// useEffect. Passing a stable array avoids that render loop.
		selectedApps: EMPTY_SELECTED_APPS,
		onAppSelected: (payload: unknown) => emit("appSelected", payload),
		onSelectionChange: (payload: unknown) => emit("selectionChange", payload)
	}
	// Caller-provided overrides win; fall back to the connector creds.
	const effectiveApiKey = props.apiKey ?? connectorApiKey.value
	const effectiveBaseUrl = props.apiBaseUrl ?? connectorBaseUrl.value
	if (effectiveApiKey) reactProps.apiKey = effectiveApiKey
	if (effectiveBaseUrl) reactProps.apiBaseUrl = effectiveBaseUrl
	if (props.initialFilterQuery) reactProps.initialFilterQuery = props.initialFilterQuery

	root.render(createElement(ShuffleMCP as never, reactProps))
}

onMounted(async () => {
	if (!container.value) return
	root = createRoot(container.value)
	// Wait for the connector creds before the first render. The package
	// fires its private/authenticated apps fetches eagerly on mount; if we
	// render with no apiKey/apiBaseUrl those fetches go to the package
	// defaults (shuffler.io, unauthed) and 401/CORS-block. Better to hold
	// off one async tick and render once with the right config.
	const creds = await fetchShuffleConnectorCredentials()
	if (creds) {
		connectorApiKey.value = creds.api_key
		connectorBaseUrl.value = creds.base_url
	}
	render()
})

// Re-render when any reactive prop changes. The shallow watch is fine
// since all our props are primitives or strings — no nested object
// identity churn to worry about.
watch(
	() => ({ ...props }),
	() => render(),
	{ deep: true }
)

onBeforeUnmount(() => {
	if (root) {
		root.unmount()
		root = null
	}
})
</script>
