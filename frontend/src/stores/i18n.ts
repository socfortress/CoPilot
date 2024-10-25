import type { Locale } from "@/lang/config"
import type { WritableComputedRef } from "vue"
import {
	dateDeDE,
	dateEnUS,
	dateEsAR,
	dateFrFR,
	dateItIT,
	dateJaJP,
	deDE,
	enUS,
	esAR,
	frFR,
	itIT,
	jaJP,
	type NDateLocale,
	type NLocale
} from "naive-ui"
import { acceptHMRUpdate, defineStore } from "pinia"
import { type ComposerTranslation, useI18n } from "vue-i18n"

export type I18nLangCode = Locale

export const useLocalesStore = defineStore("i18n", {
	state: () => ({
		locale: useI18n().locale as WritableComputedRef<I18nLangCode, string>,
		availableLocales: useI18n().availableLocales as I18nLangCode[]
	}),
	actions: {
		setLocale(locale: I18nLangCode): I18nLangCode {
			this.locale = locale
			return locale
		}
	},
	getters: {
		t(): ComposerTranslation {
			return useI18n().t
		},
		naiveuiLocales(): { code: I18nLangCode; ui: NLocale; date: NDateLocale }[] {
			return [
				{ code: "de", ui: deDE, date: dateDeDE },
				{ code: "en", ui: enUS, date: dateEnUS },
				{ code: "es", ui: esAR, date: dateEsAR },
				{ code: "fr", ui: frFR, date: dateFrFR },
				{ code: "it", ui: itIT, date: dateItIT },
				{ code: "jp", ui: jaJP, date: dateJaJP }
			]
		},
		naiveuiLocale(state): NLocale | undefined {
			return this.naiveuiLocales.find(locale => locale.code === state.locale)?.ui
		},
		naiveuiDateLocale(state): NDateLocale | undefined {
			return this.naiveuiLocales.find(locale => locale.code === state.locale)?.date
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
