import * as locales from "."

export type Locale = keyof typeof locales
export type MessageSchema = (typeof locales)[Locale]

export function getI18NConf() {
	// @ts-expect-error "locales" don't match with  [key: string]: { default: MessageSchema } }
	const localesEntries = Object.entries<{ default: MessageSchema }>(locales)

	const messages = localesEntries.reduce(
		(acc: { [key: string]: MessageSchema }, cur: [string, { default: MessageSchema }]) => {
			acc[cur[0]] = cur[1].default
			return acc
		},
		{}
	) as { [key in Locale]: MessageSchema }

	return {
		legacy: false,
		locale: "en",
		messages
	}
}
