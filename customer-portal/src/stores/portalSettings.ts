import type { PortalSettings } from "@/types/portal"
import axios from "axios"
import { defineStore } from "pinia"

const STORAGE_KEY = "customer-portal-settings"

// TODO-FE: CP refactor

export const usePortalSettingsStore = defineStore("portalSettings", {
	state: () => ({
		settings: null as PortalSettings | null,
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
		// TODO-FE: use persist with custom storage
		loadFromSessionStorage() {
			try {
				const stored = sessionStorage.getItem(STORAGE_KEY)
				if (stored) {
					const data = JSON.parse(stored)
					this.settings = data.settings
					return true
				}
			} catch (error) {
				console.error("Failed to load settings from sessionStorage:", error)
				sessionStorage.removeItem(STORAGE_KEY)
			}
			return false
		},

		saveToSessionStorage() {
			try {
				const data = {
					settings: this.settings
				}
				sessionStorage.setItem(STORAGE_KEY, JSON.stringify(data))
			} catch (error) {
				console.error("Failed to save settings to sessionStorage:", error)
			}
		},

		async fetchSettings(force = false) {
			// Try to load from sessionStorage first
			if (!force && this.loadFromSessionStorage()) {
				return
			}

			this.loading = true
			this.error = null

			try {
				const response = await axios.get("/api/customer_portal/settings")

				if (response.data.success && response.data.settings) {
					this.settings = response.data.settings
					this.saveToSessionStorage()
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
