import locales from "."

export type MessageSchema = typeof locales.en
export type Locales = keyof typeof locales

export function getI18NConf() {
	return {
		legacy: false,
		locale: "en",
		messages: locales
	}
}
