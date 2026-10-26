import type { I18nOptions } from "vue-i18n"
import type { StringKeys } from "@/types/utils"
import * as locales from "./locales"

/**
 * The portal's languages (#1310). English is the source language and the fallback: every key
 * exists in English first, and a missing translation shows the English text. Which languages a
 * user may pick is decided per customer in CoPilot (the server answers it in `/customer_portal/me`);
 * these are every language the portal ships. The backend's list
 * (`app/customer_portal/utils/locales.py`) names the same codes.
 */
export const SUPPORTED_LOCALES = ["en", "it", "de", "fr", "es", "nl", "cs"] as const
export const DEFAULT_LOCALE = "en"

export type LocaleCodes = (typeof SUPPORTED_LOCALES)[number]
export type MessageSchema = typeof locales.en
export type I18nString = StringKeys<MessageSchema>

/** Each language in its own name, as a picker lists it: a reader finds theirs whatever is shown. */
export const LOCALE_NAMES: Record<LocaleCodes, string> = {
	en: "English",
	it: "Italiano",
	de: "Deutsch",
	fr: "Français",
	es: "Español",
	nl: "Nederlands",
	cs: "Čeština"
}

export function isLocaleCode(value: unknown): value is LocaleCodes {
	return typeof value === "string" && (SUPPORTED_LOCALES as readonly string[]).includes(value)
}

/**
 * Czech plurals: one (1), few (2–4) and many (0, 5+). A Czech message may therefore carry one form
 * more than the English one: English "one | other" is Czech "one | few | many", and English
 * "zero | one | other" is Czech "zero | one | few | many". Any other count of forms follows the
 * English rule, so a message translated with English's shape still reads.
 */
export function czechPlural(choice: number, choicesLength: number): number {
	const n = Math.abs(choice)
	const few = n >= 2 && n <= 4
	if (choicesLength === 3) return n === 1 ? 0 : few ? 1 : 2
	if (choicesLength === 4) return n === 0 ? 0 : n === 1 ? 1 : few ? 2 : 3
	if (choicesLength === 2) return n === 1 ? 0 : 1
	return Math.min(n, choicesLength - 1)
}

export function getI18NConf() {
	return {
		legacy: false,
		locale: DEFAULT_LOCALE,
		fallbackLocale: DEFAULT_LOCALE,
		messages: { ...locales } as Record<LocaleCodes, MessageSchema>,
		// A key missing in a language falls back to English quietly; one missing in English too
		// is a bug the locales test catches.
		missingWarn: false,
		fallbackWarn: false,
		warnHtmlMessage: false,
		pluralRules: { cs: czechPlural }
	} satisfies I18nOptions
}
