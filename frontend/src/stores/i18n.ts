import { acceptHMRUpdate, defineStore } from "pinia"
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
		// @ts-expect-error "Type instantiation is excessively deep and possibly infinite" ts(2589)
		pick: ["locale"]
	}
})

if (import.meta.hot) {
	import.meta.hot.accept(acceptHMRUpdate(useLocalesStore, import.meta.hot))
}
