import { useI18n } from "vue-i18n"
import { useLocalesStore } from "@/stores/i18n"

export function useStoreI18n() {
	const { t } = useI18n()

	return {
		initLocale: (): string => {
			return useLocalesStore().locale
		},
		getAvailableLocales: (): string[] => {
			return useLocalesStore().available
		},
		getLocale: (): string => {
			return useLocalesStore().locale
		},
		setLocale: (newLocale: string): string => {
			useLocalesStore().setLocale(newLocale)
			return newLocale
		},
		t
	}
}
