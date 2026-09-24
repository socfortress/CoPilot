import type { EffectivePortalBranding, PortalSettings } from "@/types/portal"
import { defineStore } from "pinia"
import Api from "@/api"
import { API_ROOT, HttpClient } from "@/api/httpClient"
import { useAuthStore } from "@/stores/auth"
import { getAvatar } from "@/utils"
import { getNameInitials } from "@/utils/format"

/**
 * Portal branding, in two layers:
 *
 * - `settings` — the global defaults. Public, so the login page can render before
 *   any customer is known.
 * - `branding` — the branding resolved for the authenticated user, i.e. their
 *   customer's override where one is configured. Only available once logged in.
 *
 * The getters read `branding` first and fall back to `settings`, so a customer
 * without an override (or a logged-out visitor) always sees the global defaults.
 */
export const usePortalSettingsStore = defineStore("portalSettings", {
	state: () => ({
		settings: null as PortalSettings | null,
		branding: null as EffectivePortalBranding | null,
		/** Object URL of the branding logo. Not persisted: it dies with the page. */
		brandingLogo: null as string | null,
		loading: false
	}),

	getters: {
		portalTitle(state) {
			return state.branding?.title || state.settings?.title || ""
		},
		portalLogo(state) {
			const globalLogo = state.settings?.logo_url ? `${API_ROOT}${state.settings.logo_url}` : null
			if (state.branding) {
				if (!state.branding.logo_url) return null
				// Until the authenticated logo has been fetched, show the global one
				// (usually the same image) rather than flashing the initials.
				return state.brandingLogo ?? globalLogo
			}
			return globalLogo
		},
		portalInitials(): string {
			return getNameInitials(this.portalTitle || "")
		},
		portalLogoInitials(): string {
			return getAvatar({ seed: this.portalInitials, text: this.portalInitials, size: 64 })
		}
	},

	actions: {
		async fetchSettings() {
			this.loading = true

			try {
				const response = await Api.portal.getSettings()

				if (response.data.success && response.data.settings) {
					this.settings = response.data.settings
				}
			} catch (error) {
				console.error("Failed to load portal settings:", error)
			} finally {
				this.loading = false
			}
		},

		/** Resolve the branding for the logged-in user (per-customer override, else global). */
		async fetchEffectiveBranding() {
			try {
				const response = await Api.portal.getEffectiveSettings()

				if (response.data.success && response.data.settings) {
					this.branding = response.data.settings
					await this.loadBrandingLogo()
				}
			} catch (error) {
				// Branding must never block the portal: keep whatever we already have
				// (the global defaults at worst).
				console.error("Failed to load customer branding:", error)
			}
		},

		/**
		 * The branding logo needs the Bearer token, which an `<img>` cannot send, so it is
		 * fetched through the HTTP client (the browser's HTTP cache still applies) and
		 * shown as an object URL.
		 */
		async loadBrandingLogo() {
			const url = this.branding?.logo_url
			if (!url) {
				this.setBrandingLogo(null)
				return
			}

			try {
				const response = await HttpClient.get<Blob>(url, { responseType: "blob" })
				this.setBrandingLogo(URL.createObjectURL(response.data))
			} catch (error) {
				console.error("Failed to load customer branding logo:", error)
				this.setBrandingLogo(null)
			}
		},

		setBrandingLogo(objectUrl: string | null) {
			if (this.brandingLogo) URL.revokeObjectURL(this.brandingLogo)
			this.brandingLogo = objectUrl
		},

		clearBranding() {
			this.branding = null
			this.setBrandingLogo(null)
		},

		/**
		 * Load the branding appropriate to the current auth state. Called on boot and
		 * whenever the user logs in or out, so a per-customer override is picked up
		 * right after login and dropped again on logout.
		 */
		async syncBranding() {
			if (!this.settings) {
				await this.fetchSettings()
			}

			if (useAuthStore().isLogged) {
				await this.fetchEffectiveBranding()
			} else {
				this.clearBranding()
			}
		}
	},
	persist: [
		{
			storage: sessionStorage,
			pick: ["settings", "branding"]
		}
	]
})
