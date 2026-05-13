// Force `@shuffleio/shuffle-mcps`'s global API base URL to our
// same-origin proxy at module init, regardless of build-time env vars.
//
// Why this exists: the package's components beyond `<ShuffleMCP>`
// (AppDetailDrawer, TryMcpSection, SingulActionsPreview, the auth/lookup
// hooks) ignore `apiBaseUrl` props and only honour the internal
// `API_CONFIG.baseUrl` getter. That getter resolves via:
//
//   import.meta.env.VITE_SHUFFLE_API_URL || window.location.origin
//
// We tried injecting the env var via Vite's `define`, a vite.config.ts
// `process.env` assignment, and a developer-local `frontend/.env` —
// each fell over in some combination of: Vite caching pre-bundled deps
// in `node_modules/.vite`, `define` not text-replacing inside the
// optimized package bundle, `.env` being gitignored and missing on
// fresh clones, or HMR not picking up env changes without a full
// restart.
//
// Runtime override is reliable: `API_CONFIG.baseUrl` is a JS getter on
// a plain object, so `Object.defineProperty` replaces it cleanly.
// `getApiUrl(endpoint)` re-reads the getter on every request, so the
// override takes effect for all subsequent calls.
//
// Importing this module anywhere in the embed-wrapper chain ensures the
// override is in place before any Shuffle component fires its first
// fetch. The IIFE keeps the install idempotent across multiple imports.

import { API_CONFIG } from "@shuffleio/shuffle-mcps"

const SHUFFLE_PROXY_BASE = "/api/shuffle/integrations/proxy"

let installed = false

function install() {
	if (installed) return
	installed = true
	try {
		Object.defineProperty(API_CONFIG, "baseUrl", {
			get: () => SHUFFLE_PROXY_BASE,
			configurable: true
		})
	} catch (err) {
		// Defensive: if a future package version freezes API_CONFIG we'd
		// silently fall back to env-var behaviour. Log so it's debuggable.

		console.warn("[shuffle] could not override API_CONFIG.baseUrl:", err)
	}
}

install()

export {}
