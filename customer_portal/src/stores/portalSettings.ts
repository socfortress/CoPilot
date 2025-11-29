import { defineStore } from "pinia"
import axios from "axios"

interface PortalSettings {
	id: number
	title: string
	logo_base64: string
	logo_mime_type: string
	updated_at: string
}

interface PortalSettingsState {
	settings: PortalSettings | null
	loading: boolean
	error: string | null
}

export const usePortalSettingsStore = defineStore("portalSettings", {
	state: (): PortalSettingsState => ({
		settings: null,
		loading: false,
		error: null
	}),

	getters: {
		portalTitle: state => state.settings?.title || "",
		portalLogo: state => {
			if (state.settings?.logo_base64 && state.settings?.logo_mime_type) {
				return `data:${state.settings.logo_mime_type};base64,${state.settings.logo_base64}`
			}
			return null
		}
	},

	actions: {
		async fetchSettings() {
			this.loading = true
			this.error = null

			try {
				const response = await axios.get("/api/customer_portal/settings")

				if (response.data.success && response.data.settings) {
					this.settings = response.data.settings
				}
			} catch (error: any) {
				this.error = error.response?.data?.message || "Failed to load portal settings"
				console.error("Failed to load portal settings:", error)
			} finally {
				this.loading = false
			}
		}
	}
})
