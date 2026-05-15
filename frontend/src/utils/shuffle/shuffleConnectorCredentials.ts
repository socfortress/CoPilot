// Single-fetch cache for the deployment-wide Shuffle connector creds
// (URL + admin API key) used by the ShuffleMCP / TryMcp React embeds.
//
// The embed wrappers (`ShuffleMCPEmbed.vue`, `TryMcpEmbed.vue`,
// `AppDetailDrawerEmbed.vue`) call
// `fetchShuffleConnectorCredentials()` on mount. The first call hits the
// backend; subsequent calls re-use the in-flight or resolved promise so
// every embed in the session shares one round-trip. On error we cache
// `null` and don't retry — callers stay on whatever explicit overrides
// they were already passing.
//
// On first successful resolve, `setShuffleApiBaseUrl` patches the package
// global `API_CONFIG.baseUrl` so embeds that ignore props see the real
// connector URL from the DB.

import type { ShuffleConnectorCredentials } from "@/api/endpoints/shuffle"
import { API_CONFIG } from "@shuffleio/shuffle-mcps"
import Api from "@/api"

let currentBaseUrl: string | null = null
let installed = false
let cached: Promise<ShuffleConnectorCredentials | null> | null = null

function setShuffleApiBaseUrl(url: string): void {
	currentBaseUrl = url
	if (installed) return
	installed = true
	try {
		Object.defineProperty(API_CONFIG, "baseUrl", {
			get: () => currentBaseUrl ?? "",
			configurable: true
		})
	} catch (err) {
		console.warn("[shuffle] could not override API_CONFIG.baseUrl:", err)
	}
}

export function fetchShuffleConnectorCredentials(): Promise<ShuffleConnectorCredentials | null> {
	if (cached) return cached
	cached = Api.shuffle
		.getConnectorCredentials()
		.then(res => {
			if (!res.data.success) return null
			const creds: ShuffleConnectorCredentials = {
				base_url: res.data.base_url,
				api_key: res.data.api_key
			}
			setShuffleApiBaseUrl(creds.base_url)
			return creds
		})
		.catch(() => null)
	return cached
}

/** Test-only — drops the cached result so the next call re-fetches. */
export function resetShuffleConnectorCredentialsCache(): void {
	cached = null
}
