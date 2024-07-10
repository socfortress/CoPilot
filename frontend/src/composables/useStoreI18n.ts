import { useI18n } from "vue-i18n"
import { useLocalesStore } from "@/stores/i18n"

export function useStoreI18n() {
	const { t } = useI18n()
	const localesStore = useLocalesStore()

	return {
		initLocale: (): string => {
			return localesStore.locale
		},
		getAvailableLocales: (): string[] => {
			return localesStore.available
		},
		getLocale: (): string => {
			return localesStore.locale
		},
		setLocale: (newLocale: string): string => {
			localesStore.setLocale(newLocale)
			return newLocale
		},
		t
	}
}
