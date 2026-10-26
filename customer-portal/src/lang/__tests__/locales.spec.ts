import { describe, expect, it } from "vitest"
import { czechPlural, DEFAULT_LOCALE, LOCALE_NAMES, SUPPORTED_LOCALES } from "../config"
import * as locales from "../locales"

interface Messages { [key: string]: string | Messages }

/** Every leaf of a language's messages, by its dotted key. */
function leaves(messages: Messages, prefix = ""): Map<string, string> {
	const out = new Map<string, string>()
	for (const [key, value] of Object.entries(messages)) {
		const path = prefix ? `${prefix}.${key}` : key
		const nested = typeof value === "string" ? [[path, value] as const] : [...leaves(value, path)]
		for (const [k, v] of nested) out.set(k, v)
	}
	return out
}

/**
 * The `{name}` placeholders a message uses, and its linked `@:key` references, each once and sorted:
 * a plural message repeats `{count}` per form, and Czech carries one form more than English.
 */
function placeholders(message: string): string[] {
	return [...new Set([...message.matchAll(/\{\s*([\w.]+)\s*\}|@:([\w.]+)/g)].map(m => m[1] ?? `@:${m[2]}`))].sort()
}

const english = leaves(locales.en as unknown as Messages)

/** The portal's languages (#1310): English is the source, every other language carries the same keys. */
describe("the portal's languages", () => {
	it("ship exactly the supported languages, each named in its own language", () => {
		expect(Object.keys(locales).sort()).toEqual([...SUPPORTED_LOCALES].sort())
		expect(SUPPORTED_LOCALES[0]).toBe(DEFAULT_LOCALE)
		expect(Object.keys(LOCALE_NAMES).sort()).toEqual([...SUPPORTED_LOCALES].sort())
	})

	it("have no empty English text", () => {
		const empty = [...english].filter(([, text]) => !text.trim()).map(([key]) => key)
		expect(empty).toEqual([])
	})

	describe.each(SUPPORTED_LOCALES.filter(code => code !== DEFAULT_LOCALE))("%s", code => {
		const messages = leaves(locales[code] as unknown as Messages)

		it("has every English key and no other", () => {
			const missing = [...english.keys()].filter(key => !messages.has(key))
			const extra = [...messages.keys()].filter(key => !english.has(key))
			expect({ missing, extra }).toEqual({ missing: [], extra: [] })
		})

		it("has no empty text", () => {
			const empty = [...messages].filter(([, text]) => !text.trim()).map(([key]) => key)
			expect(empty).toEqual([])
		})

		it("keeps every placeholder and plural form of the English text", () => {
			const wrong = [...english]
				.filter(([key]) => messages.has(key))
				.filter(([key, text]) => {
					const translated = messages.get(key) ?? ""
					const forms = text.split(" | ").length
					const translatedForms = translated.split(" | ").length
					// Czech may carry its "few" form (2–4) on top of English's (see czechPlural).
					const formsOk = translatedForms === forms || (code === "cs" && forms > 1 && translatedForms === forms + 1)
					return placeholders(text).join() !== placeholders(translated).join() || !formsOk
				})
				.map(([key]) => key)
			expect(wrong).toEqual([])
		})
	})
})

describe("czech plurals", () => {
	it("pick one, few or many in a three-form message", () => {
		expect([1, 2, 4, 5, 0, 22].map(n => czechPlural(n, 3))).toEqual([0, 1, 1, 2, 2, 2])
	})

	it("pick zero, one, few or many in a four-form message", () => {
		expect([0, 1, 3, 7].map(n => czechPlural(n, 4))).toEqual([0, 1, 2, 3])
	})

	it("read an English-shaped two-form message like English", () => {
		expect([1, 2, 9].map(n => czechPlural(n, 2))).toEqual([0, 1, 1])
	})
})
