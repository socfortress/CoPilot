import type { I18nOptions } from "vue-i18n"
import type { RecursiveKeyOf } from "@/types/common"
import * as locales from "./locales"

export type LocaleCodes = keyof typeof locales
export type MessageSchema = (typeof locales)[LocaleCodes]
export type I18nString = RecursiveKeyOf<MessageSchema>

export function getI18NConf() {
	const localesEntries = Object.entries<MessageSchema>(locales)

	const messages = localesEntries.reduce((acc: { [key: string]: MessageSchema }, cur: [string, MessageSchema]) => {
		acc[cur[0]] = cur[1]
		return acc
	}, {}) as { [key in LocaleCodes]: MessageSchema }

	return {
		legacy: false,
		locale: "en",
		messages
	} satisfies I18nOptions
}
