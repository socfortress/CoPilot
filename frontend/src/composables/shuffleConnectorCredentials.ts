import type { ShuffleConnectorCredentials } from "@/api/endpoints/shuffle"
// Single-fetch cache for the deployment-wide Shuffle connector creds
// (URL + admin API key) used by the ShuffleMCP / TryMcp React embeds.
//
// The embed wrappers (`ShuffleMCPEmbed.vue`, `TryMcpEmbed.vue`) call
// `fetchShuffleConnectorCredentials()` on mount. The first call hits the
// backend; subsequent calls re-use the in-flight or resolved promise so
// every embed in the session shares one round-trip. On error we cache
// `null` and don't retry — callers stay on whatever explicit overrides
// they were already passing.
import Api from "@/api"

let cached: Promise<ShuffleConnectorCredentials | null> | null = null

export function fetchShuffleConnectorCredentials(): Promise<ShuffleConnectorCredentials | null> {
	if (cached) return cached
	cached = Api.shuffle
		.getConnectorCredentials()
		.then(res => {
			if (!res.data.success) return null
			return { base_url: res.data.base_url, api_key: res.data.api_key }
		})
		.catch(() => null)
	return cached
}

/** Test-only — drops the cached result so the next call re-fetches. */
export function resetShuffleConnectorCredentialsCache(): void {
	cached = null
}
