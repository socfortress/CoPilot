/**
 * The Customer Portal's languages (#1310), in the portal's order: English first, always enabled and the
 * default. Must match the backend's `customer_portal/utils/locales.py:SUPPORTED_LOCALES` and the portal's
 * `lang/config.ts:SUPPORTED_LOCALES` (`backend/tests/test_customer_portal_languages.py` compares them).
 */
export const PORTAL_LANGUAGES = ["en", "it", "de", "fr", "es", "nl", "cs"] as const

export type PortalLanguage = (typeof PORTAL_LANGUAGES)[number]

export const DEFAULT_PORTAL_LANGUAGE: PortalLanguage = "en"

/** Each language in English (what the SOC reads) and in its own language (what the customer sees). */
export const PORTAL_LANGUAGE_NAMES: Record<PortalLanguage, { english: string; native: string }> = {
	en: { english: "English", native: "English" },
	it: { english: "Italian", native: "Italiano" },
	de: { english: "German", native: "Deutsch" },
	fr: { english: "French", native: "Français" },
	es: { english: "Spanish", native: "Español" },
	nl: { english: "Dutch", native: "Nederlands" },
	cs: { english: "Czech", native: "Čeština" }
}

export function isPortalLanguage(code: string): code is PortalLanguage {
	return (PORTAL_LANGUAGES as readonly string[]).includes(code)
}

/** A set to save: known languages only, in the portal's order, English always included. */
export function normalizeLanguages(codes: readonly string[]): PortalLanguage[] {
	const picked = new Set(codes.filter(isPortalLanguage))
	picked.add(DEFAULT_PORTAL_LANGUAGE)
	return PORTAL_LANGUAGES.filter(code => picked.has(code))
}

export function sameLanguages(a: readonly string[], b: readonly string[]): boolean {
	const x = normalizeLanguages(a)
	const y = normalizeLanguages(b)
	return x.length === y.length && x.every((code, i) => code === y[i])
}
