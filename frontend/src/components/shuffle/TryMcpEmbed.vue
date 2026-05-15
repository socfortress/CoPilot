<template>
	<div ref="container" class="w-full" />
</template>

<script setup lang="ts">
// Vue wrapper around `<TryMcpSection>` (a React component from
// `@shuffleio/shuffle-mcps`). Same manual react-dom/client mount
// strategy as ShuffleMCPEmbed.
//
// Difference from ShuffleMCPEmbed: TryMcpSection requires a *resolved*
// app id (Algolia objectID), not just a name. The package's
// `useAppLookup(name)` hook does the resolution, so we wrap both in a
// tiny inline React component and let the hook drive what gets rendered.
//
// Auth: TryMcpSection reads from the package's global API_CONFIG rather
// than props. We call `API_CONFIG.setApiKey(authToken)` once on mount —
// good enough for a single-customer prototype. Multi-customer scoping
// (per-org headers via `getAuthHeader(orgId)`) is a follow-up.

import type { FC } from "react"
import type { Root } from "react-dom/client"
import { API_CONFIG, TryMcpSection, useAppLookup } from "@shuffleio/shuffle-mcps"
import { storeToRefs } from "pinia"
import { createElement } from "react"
import { createRoot } from "react-dom/client"
import { onBeforeUnmount, onMounted, ref, watch } from "vue"
import { useThemeStore } from "@/stores/theme"
import { fetchShuffleConnectorCredentials } from "@/utils/shuffle/shuffleConnectorCredentials"
import { MuiProvider } from "@/utils/shuffle/shuffleMuiTheme"

interface Props {
	appName: string
	/**
	 * Per-customer Shuffle org auth token. Forwarded to TryMcpSection's
	 * underlying chat so per-customer scoping holds even when the
	 * deployment-wide connector API key is also set.
	 */
	authToken: string
}

const props = defineProps<Props>()

const container = ref<HTMLElement | null>(null)
let root: Root | null = null

const themeStore = useThemeStore()
const { isThemeDark } = storeToRefs(themeStore)

// Inline React component that resolves appName → algoliaId via the
// package's hook, then mounts TryMcpSection. Lives inline (not a
// separate .tsx file) because it's tightly coupled to this wrapper and
// has no other consumers.
const TryMcpInline: FC<{ appName: string }> = ({ appName }) => {
	const { displayName, image, categories, algoliaId, loading } = useAppLookup(appName)
	if (loading) {
		return createElement("div", { className: "text-tertiary text-center text-sm" }, "Resolving app…")
	}
	if (!algoliaId) {
		return createElement(
			"div",
			{ className: "text-error p-4 text-sm" },
			`Could not resolve "${appName}" against Shuffle's catalog.`
		)
	}
	return createElement(TryMcpSection as never, {
		appName: displayName,
		appIcon: image,
		appId: algoliaId,
		categories
	})
}

function render() {
	if (!root) return
	root.render(
		createElement(
			MuiProvider as never,
			{ isDark: isThemeDark.value },
			createElement(TryMcpInline, { appName: props.appName })
		)
	)
}

onMounted(async () => {
	if (!container.value) return
	root = createRoot(container.value)
	// Resolve creds before the first render — same reason as
	// ShuffleMCPEmbed. The package's hooks (useAppLookup, the chat fetch)
	// fire on mount; rendering them with the wrong API key burns
	// unauthenticated requests to shuffler.io.
	const creds = await fetchShuffleConnectorCredentials()
	API_CONFIG.setApiKey(creds?.api_key ?? props.authToken)
	render()
})

watch(
	() => [props.appName, props.authToken] as const,
	() => {
		// Don't clobber the connector key if it's already loaded —
		// fetchShuffleConnectorCredentials caches across the session.
		fetchShuffleConnectorCredentials().then(creds => {
			API_CONFIG.setApiKey(creds?.api_key ?? props.authToken)
			render()
		})
	}
)

// Re-render when the host theme toggles so the MUI provider swaps to
// the matching light/dark palette.
watch(isThemeDark, () => render())

onBeforeUnmount(() => {
	if (root) {
		root.unmount()
		root = null
	}
})
</script>
