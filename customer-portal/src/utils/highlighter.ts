import type { HighlighterCore } from "shiki/core"
import { createHighlighterCore } from "shiki/core"
import { createJavaScriptRegexEngine } from "shiki/engine/javascript"

const THEME_LIGHT = "slack-ochin"
const THEME_DARK = "aurora-x"
const LEADING_WHITESPACE_REGEX = /^\s+/
const TAB_REGEX = /\t/g

/** Anything outside the languages below renders as plain text rather than failing. */
export const FALLBACK_LANGUAGE = "text"

/**
 * The languages the portal can highlight. Each is downloaded only when a block needs it:
 * a report without code must not fetch sixteen grammars (and their split chunks) just
 * because the highlighter was created.
 */
const LANGUAGES = {
	javascript: () => import("shiki/langs/javascript.mjs"),
	typescript: () => import("shiki/langs/typescript.mjs"),
	powershell: () => import("shiki/langs/powershell.mjs"),
	shellscript: () => import("shiki/langs/shellscript.mjs"),
	json: () => import("shiki/langs/json.mjs"),
	xml: () => import("shiki/langs/xml.mjs"),
	yaml: () => import("shiki/langs/yaml.mjs"),
	html: () => import("shiki/langs/html.mjs"),
	scss: () => import("shiki/langs/scss.mjs"),
	css: () => import("shiki/langs/css.mjs"),
	csharp: () => import("shiki/langs/csharp.mjs"),
	http: () => import("shiki/langs/http.mjs"),
	sql: () => import("shiki/langs/sql.mjs"),
	lua: () => import("shiki/langs/lua.mjs"),
	vb: () => import("shiki/langs/vb.mjs"),
	php: () => import("shiki/langs/php.mjs")
} as const

type Language = keyof typeof LANGUAGES

/** The short names people write after ``` for the languages above (shiki's own aliases). */
const ALIASES: Record<string, Language> = {
	js: "javascript",
	cjs: "javascript",
	mjs: "javascript",
	ts: "typescript",
	cts: "typescript",
	mts: "typescript",
	ps: "powershell",
	ps1: "powershell",
	pwsh: "powershell",
	bash: "shellscript",
	sh: "shellscript",
	shell: "shellscript",
	zsh: "shellscript",
	yml: "yaml",
	"c#": "csharp",
	cs: "csharp"
}

const FENCE_REGEX = /^[ \t]*(?:`{3,}|~{3,})[ \t]*([^\s`~{]+)/gm

let highlighterInstance: HighlighterCore | null = null
let highlighterPromise: Promise<HighlighterCore> | null = null

/**
 * One highlighter for the whole app, built from `shiki/core` with the JavaScript regex
 * engine and no language: `loadLanguages` adds the ones a block needs. The `shiki` entry
 * point would register all ~200 bundled languages and the Oniguruma WebAssembly.
 */
export async function getHighlighter() {
	if (highlighterInstance) {
		return highlighterInstance
	}
	if (highlighterPromise) {
		return highlighterPromise
	}

	highlighterPromise = (async () => {
		highlighterInstance = await createHighlighterCore({
			themes: [import("shiki/themes/slack-ochin.mjs"), import("shiki/themes/aurora-x.mjs")],
			langs: [],
			engine: createJavaScriptRegexEngine()
		})
		return highlighterInstance
	})()

	return highlighterPromise
}

/** The portal's name for `lang` (aliases resolved), or null when it cannot highlight it. */
export function canonicalLanguage(lang: string | null | undefined): Language | null {
	const name = lang?.trim().toLowerCase()
	if (!name) return null
	return ALIASES[name] ?? (name in LANGUAGES ? (name as Language) : null)
}

/** Download the grammars the given languages need, once each; unknown ones are ignored. */
export async function loadLanguages(highlighter: HighlighterCore, langs: Iterable<string | null | undefined>) {
	const loaded = highlighter.getLoadedLanguages()
	const missing = [...new Set([...langs].map(canonicalLanguage))].filter(
		(lang): lang is Language => lang !== null && !loaded.includes(lang)
	)
	if (missing.length) {
		await highlighter.loadLanguage(...missing.map(lang => LANGUAGES[lang]))
	}
}

/** The languages named on the fenced code blocks of a Markdown text. */
export function fencedLanguages(markdown: string | null | undefined): string[] {
	return [...(markdown ?? "").matchAll(FENCE_REGEX)].map(match => match[1]!)
}

/** The loaded language to highlight `lang` with, otherwise plain text. */
export function supportedLanguage(highlighter: HighlighterCore, lang: string): string {
	const canonical = canonicalLanguage(lang)
	return canonical && highlighter.getLoadedLanguages().includes(canonical) ? canonical : FALLBACK_LANGUAGE
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
