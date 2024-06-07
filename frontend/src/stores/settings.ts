import { defineStore, acceptHMRUpdate } from "pinia"

export const useSettingsStore = defineStore("settings", {
	state: () => ({
		settings: {
			dateFormat: "MM/DD/YYYY",
			hours24: true
		},
		dateFormats: ["MM/DD/YYYY", "DD/MM/YYYY"]
	}),
	actions: {
		setDateFormat(format: string) {
			this.settings.dateFormat = format
		},
		setHours24(hours24: boolean) {
			this.settings.hours24 = hours24
		}
	},
	getters: {
		dateFormatsAvailable(state) {
			return state.dateFormats
		},
		hours24(state) {
			return state.settings.hours24
		},
		rawDateFormat(state) {
			return state.settings.dateFormat
		},
		dateFormat(state) {
			const separator = " "
			const date = state.settings.dateFormat
			const time = state.settings.hours24 ? "HH:mm" : "h:mm a"
			const timesec = state.settings.hours24 ? "HH:mm:ss" : "h:mm:ss a"
			const timesecmill = "HH:mm:ss.SSS"

			return {
				date: `${date}`,
				datetime: `${date}${separator}${time}`,
				datetimesec: `${date}${separator}${timesec}`,
				datetimesecmill: `${date}${separator}${timesecmill}`,
				/** "HH:mm" or "h:mm a" */
				time,
				/** "HH:mm:ss" or "h:mm:ss a" */
				timesec,
				timesecmill
			}
		}
	},
	persist: {
		paths: ["settings"]
	}
})

if (import.meta.hot) {
	import.meta.hot.accept(acceptHMRUpdate(useSettingsStore, import.meta.hot))
}
