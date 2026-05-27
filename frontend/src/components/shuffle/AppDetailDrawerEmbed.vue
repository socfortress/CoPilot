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

import type { Root } from "react-dom/client"
import { API_CONFIG, AppDetailDrawer } from "@shuffleio/shuffle-mcps"
import { storeToRefs } from "pinia"
import { createElement } from "react"
import { createRoot } from "react-dom/client"
import { onBeforeUnmount, onMounted, ref, watch } from "vue"
import { useThemeStore } from "@/stores/theme"
import { fetchShuffleConnectorCredentials } from "@/utils/shuffle/shuffleConnectorCredentials"
import { MuiProvider } from "@/utils/shuffle/shuffleMuiTheme"

interface Props {
	appName: string | null
	width?: number
	anchor?: "left" | "right"
}

const props = withDefaults(defineProps<Props>(), {
	width: 720,
	anchor: "right"
})

const emit = defineEmits<{
	(e: "refresh"): void
}>()

const show = defineModel<boolean>("show", { required: true, default: false })

const container = ref<HTMLElement | null>(null)
let root: Root | null = null

const themeStore = useThemeStore()
const { isThemeDark } = storeToRefs(themeStore)

function render() {
	if (!root) return
	root.render(
		createElement(
			MuiProvider as never,
			{ isDark: isThemeDark.value },
			createElement(AppDetailDrawer as never, {
				open: show.value,
				onClose: () => (show.value = false),
				appName: props.appName,
				anchor: props.anchor,
				width: props.width,
				onRefresh: () => emit("refresh")
			})
		)
	)
}

watch([show, () => props.appName, () => props.width, () => props.anchor, isThemeDark], () => render())

onBeforeUnmount(() => {
	if (root) {
		root.unmount()
		root = null
	}
})

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
</script>
