import type { PortalSettings } from "@/types/portal"
import { defineStore } from "pinia"
import Api from "@/api"
import { getAvatar } from "@/utils"
import { getNameInitials } from "@/utils/format"

export const usePortalSettingsStore = defineStore("portalSettings", {
	state: () => ({
		settings: null as PortalSettings | null,
		loading: false
	}),

	getters: {
		portalTitle(state) {
			return state.settings?.title || ""
		},
		portalLogo(state) {
			if (state.settings?.logo_base64 && state.settings?.logo_mime_type) {
				return `data:${state.settings.logo_mime_type};base64,${state.settings.logo_base64}`
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
		}
	},
	persist: [
		{
			storage: sessionStorage,
			pick: ["settings"]
		}
	]
})
