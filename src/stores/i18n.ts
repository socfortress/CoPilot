import { defineStore, acceptHMRUpdate } from "pinia"
import { useI18n } from "vue-i18n"

export const useLocalesStore = defineStore("i18n", {
	state: () => ({
		locale: useI18n().locale,
		available: useI18n().availableLocales
	}),
	actions: {
		setLocale(locale: string) {
			this.locale = locale
		}
	},
	persist: {
		paths: ["locale"]
	}
})

if (import.meta.hot) {
	import.meta.hot.accept(acceptHMRUpdate(useLocalesStore, import.meta.hot))
}
