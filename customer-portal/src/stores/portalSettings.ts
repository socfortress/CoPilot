import type { EffectivePortalBranding, PortalSettings } from "@/types/portal"
import { defineStore } from "pinia"
import Api from "@/api"
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
		loading: false
	}),

	getters: {
		portalTitle(state) {
			return state.branding?.title || state.settings?.title || ""
		},
		portalLogo(state) {
			const source = state.branding ?? state.settings
			if (source?.logo_base64 && source?.logo_mime_type) {
				return `data:${source.logo_mime_type};base64,${source.logo_base64}`
			}
			return null
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
				}
			} catch (error) {
				// Branding must never block the portal: keep whatever we already have
				// (the global defaults at worst).
				console.error("Failed to load customer branding:", error)
			}
		},

		clearBranding() {
			this.branding = null
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
