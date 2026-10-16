import type MarkdownIt from "markdown-it/lib/index.mjs"
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
			import("shiki/langs/php.mjs"),
			import("shiki/langs/python.mjs"),
			import("shiki/langs/rust.mjs"),
			import("shiki/langs/markdown.mjs"),
			import("shiki/langs/go.mjs"),
			import("shiki/langs/dart.mjs")
		],
		engine: createOnigurumaEngine(() => import("shiki/wasm"))
	}).then(instance => {
		highlighterInstance = instance
		return instance
	})

	return highlighterPromise
}

/** Languages Shiki renders as plain text without a grammar. */
const PLAIN_LANGUAGES = ["text", "txt", "plain", "plaintext"]

/**
 * A markdown-it plugin, used after `@shikijs/markdown-it`'s, that keeps a code block from blanking
 * the whole document. Shiki throws on a language it hasn't loaded (` ```kql `, ` ```yara `, a typo,
 * an info string like ` ```<img `), and an exception in `highlight` ends markdown-it's render, so
 * every block of a message used to vanish. Here a language that isn't loaded is highlighted as
 * plain `text`, and any other failure returns "" so markdown-it escapes the code itself.
 */
export function markdownItSafeHighlight(highlighter: Pick<HighlighterGeneric<string, string>, "getLoadedLanguages">) {
	return (md: MarkdownIt): void => {
		const highlight = md.options.highlight
		if (!highlight) return
		md.options.highlight = (code, lang, attrs) => {
			const loaded = highlighter.getLoadedLanguages() as string[]
			const known = !lang || PLAIN_LANGUAGES.includes(lang) || loaded.includes(lang)
			try {
				return highlight(code, known ? lang : "text", attrs)
			} catch {
				return ""
			}
		}
	}
}

/** A markdown-it plugin that renders no images: `![x](url)` stays a link, never an `<img>` that loads. */
export function markdownItNoImages(md: MarkdownIt): void {
	md.disable("image")
}

export const codeThemes = {
	light: THEME_LIGHT,
	dark: THEME_DARK
}

const LEADING_WHITESPACE_REGEX = /^\s+/
const TAB_CHAR_REGEX = /\t/g

export function resetIndent(el: HTMLElement) {
	if (el) {
		let lines: string[] = el.innerHTML?.split("\n")

		if (lines?.length) {
			if (lines[0] === "") {
				lines.shift()
			}

			const matches = LEADING_WHITESPACE_REGEX.exec(lines[0] ?? "") ?? null
			const indentation = matches !== null ? (matches[0] ?? "") : ""
			if (indentation) {
				lines = lines.map(line => {
					line = line.replace(indentation, "")
					return line.replace(TAB_CHAR_REGEX, "    ")
				})

				el.innerHTML = lines.join("\n").trim()
			}
		}
	}
}
