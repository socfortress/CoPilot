import type { NDateLocale, NLocale } from "naive-ui"
import type { WritableComputedRef } from "vue"
import type { LocaleCodes } from "@/lang/config"
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
	jaJP
} from "naive-ui"
import { acceptHMRUpdate, defineStore } from "pinia"
import { nextTick } from "vue"
import { useI18n } from "vue-i18n"
import dayjs from "@/utils/dayjs"

export const useLocalesStore = defineStore("i18n", {
	state: () => {
		nextTick(() => {
			const dayjsLocale = useLocalesStore().locale === "jp" ? "ja" : useLocalesStore().locale
			dayjs.locale(dayjsLocale)
		})

		return {
			locale: useI18n().locale as WritableComputedRef<LocaleCodes, string>,
			availableLocales: useI18n().availableLocales as LocaleCodes[]
		}
	},
	actions: {
		setLocale(locale: LocaleCodes): LocaleCodes {
			const dayjsLocale = locale === "jp" ? "ja" : locale
			dayjs.locale(dayjsLocale)
			this.locale = locale
			return locale
		}
	},
	getters: {
		naiveuiLocales(): { code: LocaleCodes; ui: NLocale; date: NDateLocale }[] {
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
