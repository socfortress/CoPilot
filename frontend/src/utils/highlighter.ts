import type { BundledLanguage, BundledTheme, HighlighterGeneric } from "shiki"
import { createHighlighter } from "shiki"
import { createOnigurumaEngine } from "shiki/engine/oniguruma"

const THEME_LIGHT = "slack-ochin"
const THEME_DARK = "aurora-x"

let highlighterInstance: HighlighterGeneric<BundledLanguage, BundledTheme> | null = null
let highlighterPromise: Promise<HighlighterGeneric<BundledLanguage, BundledTheme>> | null = null

export async function getHighlighter() {
	if (highlighterInstance) {
		return highlighterInstance
	}
	if (highlighterPromise) {
		return highlighterPromise
	}

	highlighterPromise = createHighlighter({
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
		engine: createOnigurumaEngine(() => import("shiki/wasm"))
	}).then(instance => {
		highlighterInstance = instance
		return instance
	})

	return highlighterPromise
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

			const matches = /^\s+/.exec(lines[0])
			const indentation = matches !== null ? matches[0] : null
			if (indentation) {
				lines = lines.map(line => {
					line = line.replace(indentation, "")
					return line.replace(/\t/g, "    ")
				})

				el.innerHTML = lines.join("\n").trim()
			}
		}
	}
}
