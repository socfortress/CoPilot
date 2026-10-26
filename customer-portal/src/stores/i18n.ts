import type { NDateLocale, NLocale } from "naive-ui"
import type { LocaleCodes } from "@/lang/config"
import { csCZ, dateCsCZ, dateDeDE, dateEnUS, dateEsAR, dateFrFR, dateItIT, dateNlNL, deDE, enUS, esAR, frFR, itIT, nlNL } from "naive-ui"
import { acceptHMRUpdate, defineStore } from "pinia"
import Api from "@/api"
import i18n from "@/lang"
import { DEFAULT_LOCALE, isLocaleCode, SUPPORTED_LOCALES } from "@/lang/config"
import dayjs from "@/utils/dayjs"

/** naive-ui's own texts (pickers, pagination, empty states) in each portal language. */
const NAIVE_LOCALES: Record<LocaleCodes, { ui: NLocale; date: NDateLocale }> = {
	en: { ui: enUS, date: dateEnUS },
	it: { ui: itIT, date: dateItIT },
	de: { ui: deDE, date: dateDeDE },
	fr: { ui: frFR, date: dateFrFR },
	es: { ui: esAR, date: dateEsAR },
	nl: { ui: nlNL, date: dateNlNL },
	cs: { ui: csCZ, date: dateCsCZ }
}

/** The browser's first language that the user may pick, if any. */
export function browserLocale(available: readonly string[], languages: readonly string[] = navigator.languages ?? []): LocaleCodes | null {
	for (const language of languages) {
		const code = language.split("-")[0]?.toLowerCase()
		if (isLocaleCode(code) && available.includes(code)) return code
	}
	return null
}

/**
 * The portal's language (#1310). Which languages a user may pick is the customers' choice, made in
 * CoPilot: the server answers it in `/customer_portal/me`, with the user's own pick, kept on their
 * account so it follows them to any device. English is always available and is the default.
 *
 * Not persisted in the browser: the next user of a shared machine starts in English, and the
 * signed-in user's language comes back from the server at every page load.
 */
export const useLocalesStore = defineStore("i18n", {
	state: () => ({
		locale: DEFAULT_LOCALE as LocaleCodes,
		available: [DEFAULT_LOCALE] as LocaleCodes[],
		saving: false
	}),
	actions: {
		/** Show the portal in ``locale``: vue-i18n, naive-ui, dayjs and the page's `lang`. */
		apply(locale: LocaleCodes): LocaleCodes {
			this.locale = locale
			i18n.global.locale.value = locale
			dayjs.locale(locale)
			if (typeof document !== "undefined") document.documentElement.lang = locale
			return locale
		},
		/** The server's answer (`/customer_portal/me`): what the user may pick and what to show. */
		applyProfile(profile: { locale?: string; available_locales?: string[]; locale_chosen?: boolean }) {
			const available = (profile.available_locales ?? []).filter(isLocaleCode)
			this.available = SUPPORTED_LOCALES.filter(code => code === DEFAULT_LOCALE || available.includes(code))
			const fromServer = isLocaleCode(profile.locale) && this.available.includes(profile.locale) ? profile.locale : DEFAULT_LOCALE
			// Nothing picked yet: the browser's language, when the user's customers offer it.
			const locale = profile.locale_chosen ? fromServer : (browserLocale(this.available) ?? fromServer)
			this.apply(locale)
		},
		/** The user picks a language: stored on their account, then shown. */
		async choose(locale: LocaleCodes) {
			if (!this.available.includes(locale) || this.saving) return
			this.saving = true
			try {
				const res = await Api.languages.setMine(locale)
				const available = (res.data.available ?? []).filter(isLocaleCode)
				if (available.length) this.available = SUPPORTED_LOCALES.filter(code => available.includes(code))
				this.apply(isLocaleCode(res.data.locale) ? res.data.locale : locale)
			} finally {
				this.saving = false
			}
		},
		/** At logout: English, and English only, for whoever signs in next. */
		reset() {
			this.available = [DEFAULT_LOCALE]
			this.apply(DEFAULT_LOCALE)
		}
	},
	getters: {
		naiveuiLocale(state): NLocale {
			return NAIVE_LOCALES[state.locale].ui
		},
		naiveuiDateLocale(state): NDateLocale {
			return NAIVE_LOCALES[state.locale].date
		},
		/** More than English to pick from: the picker is worth showing. */
		canChoose(state): boolean {
			return state.available.length > 1
		}
	}
})

if (import.meta.hot) {
	import.meta.hot.accept(acceptHMRUpdate(useLocalesStore, import.meta.hot))
}
