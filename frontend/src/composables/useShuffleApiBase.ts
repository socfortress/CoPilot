// Forza l'URL base globale di `@shuffleio/shuffle-mcps` verso il proxy
// same-origin, indipendentemente dalle env di build.
//
// Perché esiste: componenti oltre `<ShuffleMCP>` (AppDetailDrawer,
// TryMcpSection, …) ignorano le prop `apiBaseUrl` e usano solo
// `API_CONFIG.baseUrl`. Override runtime via `Object.defineProperty` sul
// getter è affidabile; `getApiUrl` rilegge il getter a ogni richiesta.
//
// Chiamare `install()` una volta all'avvio dell'app (es. da `App.vue`):
// l'install è idempotente.

import { API_CONFIG } from "@shuffleio/shuffle-mcps"

const SHUFFLE_PROXY_BASE = import.meta.env.VITE_SHUFFLE_API_BASE_URL

let installed = false

export function useShuffleApiBase() {
	function install() {
		if (installed) return
		installed = true
		try {
			Object.defineProperty(API_CONFIG, "baseUrl", {
				get: () => SHUFFLE_PROXY_BASE,
				configurable: true
			})
		} catch (err) {
			console.warn("[shuffle] could not override API_CONFIG.baseUrl:", err)
		}
	}

	return { install }
}
