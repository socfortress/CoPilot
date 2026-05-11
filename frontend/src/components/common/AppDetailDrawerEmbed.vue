<template>
	<div ref="container" />
</template>

<script setup lang="ts">
// Vue wrapper around `<AppDetailDrawer>` (a React component from
// `@shuffleio/shuffle-mcps`). Same manual `react-dom/client` mount
// pattern as ShuffleMCPEmbed / TryMcpEmbed.
//
// AppDetailDrawer is the all-in-one panel for a single app: header
// + auth card (inline form for API-key apps, redirect handoff for
// OAuth apps) + MCP chat + Singul actions playground. We use it after
// picking an app from <ShuffleMCP preventDefault> so the user lands
// on a CoPilot-orchestrated drawer instead of a top-level redirect.

// Side-effect import: overrides API_CONFIG.baseUrl to point at our
// same-origin proxy. Must come before the `@shuffleio/shuffle-mcps`
// import so the override is in place when the package initialises.
import "@/composables/installShuffleApiBase"
import type { Root } from "react-dom/client"
import { API_CONFIG, AppDetailDrawer } from "@shuffleio/shuffle-mcps"
import { createElement } from "react"
import { createRoot } from "react-dom/client"
import { onBeforeUnmount, onMounted, ref, watch } from "vue"
import { fetchShuffleConnectorCredentials } from "@/composables/shuffleConnectorCredentials"

interface Props {
	open: boolean
	appName: string | null
	width?: number
	anchor?: "left" | "right"
}

const props = withDefaults(defineProps<Props>(), {
	width: 720,
	anchor: "right"
})

const emit = defineEmits<{
	(e: "update:open", value: boolean): void
	(e: "refresh"): void
}>()

const container = ref<HTMLElement | null>(null)
let root: Root | null = null

function render() {
	if (!root) return
	root.render(
		createElement(AppDetailDrawer as never, {
			open: props.open,
			onClose: () => emit("update:open", false),
			appName: props.appName,
			anchor: props.anchor,
			width: props.width,
			onRefresh: () => emit("refresh")
		})
	)
}

onMounted(async () => {
	if (!container.value) return
	root = createRoot(container.value)
	// Same gating as the other embeds — wait for connector creds before
	// the first render so the drawer's internal fetches go through the
	// proxy with the right Bearer token.
	const creds = await fetchShuffleConnectorCredentials()
	if (creds?.api_key) {
		API_CONFIG.setApiKey(creds.api_key)
	}
	render()
})

watch(
	() => [props.open, props.appName, props.width, props.anchor] as const,
	() => render()
)

onBeforeUnmount(() => {
	if (root) {
		root.unmount()
		root = null
	}
})
</script>
