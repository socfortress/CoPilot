import { useLocalesStore } from "@/stores/i18n"

export function initLocale(): string {
	return useLocalesStore().locale
}
export function getAvailableLocales(): string[] {
	return useLocalesStore().available
}
export function getLocale(): string {
	return useLocalesStore().locale
}
export function setLocale(newLocale: string): string {
	useLocalesStore().setLocale(newLocale)
	return newLocale
}
