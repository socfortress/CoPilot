import type { HighlighterCore } from "shiki/core"
import { createHighlighterCore } from "shiki/core"
import { createJavaScriptRegexEngine } from "shiki/engine/javascript"

const THEME_LIGHT = "slack-ochin"
const THEME_DARK = "aurora-x"
const LEADING_WHITESPACE_REGEX = /^\s+/
const TAB_REGEX = /\t/g

/** Anything outside the languages loaded below renders as plain text rather than failing. */
export const FALLBACK_LANGUAGE = "text"

let highlighterInstance: HighlighterCore | null = null
let highlighterPromise: Promise<HighlighterCore> | null = null

/**
 * One highlighter for the whole app, built from `shiki/core`: only the themes and
 * languages listed here are bundled, and the regex engine is plain JavaScript. The
 * `shiki` entry point would register all ~200 bundled languages (each a lazy chunk)
 * and the Oniguruma WebAssembly, none of which the portal uses.
 */
export async function getHighlighter() {
	if (highlighterInstance) {
		return highlighterInstance
	}
	if (highlighterPromise) {
		return highlighterPromise
	}

	highlighterPromise = createHighlighterCore({
		themes: [import("shiki/themes/slack-ochin.mjs"), import("shiki/themes/aurora-x.mjs")],
		langs: [
			import("shiki/langs/javascript.mjs"),
			import("shiki/langs/typescript.mjs"),
			import("shiki/langs/powershell.mjs"),
			import("shiki/langs/shellscript.mjs"),
			import("shiki/langs/json.mjs"),
			import("shiki/langs/xml.mjs"),
			import("shiki/langs/yaml.mjs"),
			import("shiki/langs/html.mjs"),
			import("shiki/langs/scss.mjs"),
			import("shiki/langs/css.mjs"),
			import("shiki/langs/csharp.mjs"),
			import("shiki/langs/http.mjs"),
			import("shiki/langs/sql.mjs"),
			import("shiki/langs/lua.mjs"),
			import("shiki/langs/vb.mjs"),
			import("shiki/langs/php.mjs")
		],
		engine: createJavaScriptRegexEngine()
	}).then(instance => {
		highlighterInstance = instance
		return instance
	})

	return highlighterPromise
}

/** `lang` when the highlighter has it, otherwise plain text. */
export function supportedLanguage(highlighter: HighlighterCore, lang: string): string {
	return highlighter.getLoadedLanguages().includes(lang) ? lang : FALLBACK_LANGUAGE
}

export const codeThemes = {
	light: THEME_LIGHT,
	dark: THEME_DARK
}

export function resetIndent(el: HTMLElement) {
	if (el) {
		let lines: string[] = el.innerHTML?.split("\n")

		if (lines?.length) {
			if (lines[0] === "") {
				lines.shift()
			}

			const firstLine = lines[0]

			if (!firstLine) return

			const matches = LEADING_WHITESPACE_REGEX.exec(firstLine)
			const indentation = matches !== null ? matches[0] : null
			if (indentation) {
				lines = lines.map(line => {
					line = line.replace(indentation, "")
					return line.replace(TAB_REGEX, "    ")
				})

				el.innerHTML = lines.join("\n").trim()
			}
		}
	}
}
