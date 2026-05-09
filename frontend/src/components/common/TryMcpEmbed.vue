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

import type { Root } from "react-dom/client"
import { API_CONFIG, TryMcpSection, useAppLookup } from "@shuffleio/shuffle-mcps"
import { createElement, type FC } from "react"
import { createRoot } from "react-dom/client"
import { onBeforeUnmount, onMounted, ref, watch } from "vue"
import { fetchShuffleConnectorCredentials } from "@/composables/shuffleConnectorCredentials"

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

// Inline React component that resolves appName → algoliaId via the
// package's hook, then mounts TryMcpSection. Lives inline (not a
// separate .tsx file) because it's tightly coupled to this wrapper and
// has no other consumers.
const TryMcpInline: FC<{ appName: string }> = ({ appName }) => {
	const { displayName, image, categories, algoliaId, loading } = useAppLookup(appName)
	if (loading) {
		return createElement("div", { className: "text-tertiary p-4 text-sm" }, "Resolving app…")
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
	root.render(createElement(TryMcpInline, { appName: props.appName }))
}

onMounted(async () => {
	if (!container.value) return
	// Default to the per-customer org auth token until we resolve the
	// deployment-wide connector creds. The connector API key is the right
	// one for `/api/v1/apps` (private apps lookup) — without it the
	// browser hits CORS against shuffler.io. The org token is a usable
	// fallback when no Shuffle connector is configured.
	API_CONFIG.setApiKey(props.authToken)
	root = createRoot(container.value)
	render()
	const creds = await fetchShuffleConnectorCredentials()
	if (creds?.api_key) {
		API_CONFIG.setApiKey(creds.api_key)
		render()
	}
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

onBeforeUnmount(() => {
	if (root) {
		root.unmount()
		root = null
	}
})
</script>
