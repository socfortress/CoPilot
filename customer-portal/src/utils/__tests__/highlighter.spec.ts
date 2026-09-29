import { describe, expect, it } from "vitest"
import {
	canonicalLanguage,
	codeThemes,
	FALLBACK_LANGUAGE,
	fencedLanguages,
	getHighlighter,
	loadLanguages,
	supportedLanguage
} from "../highlighter"

// These tests share one highlighter (it is a module singleton), so they only ever add
// languages: each asserts on languages no earlier test loads.

describe("highlighter", () => {
	it("is built once and reused", async () => {
		const [first, second] = await Promise.all([getHighlighter(), getHighlighter()])
		expect(first).toBe(second)
		expect(await getHighlighter()).toBe(first)
	})

	it("starts with no language: nothing is downloaded until a block needs it", async () => {
		expect((await getHighlighter()).getLoadedLanguages()).toEqual([])
	})

	it("loads only the languages asked for, aliases included", async () => {
		const highlighter = await getHighlighter()
		await loadLanguages(highlighter, ["ps1"])
		const loaded = highlighter.getLoadedLanguages()
		expect(loaded).toContain("powershell")
		expect(loaded).not.toContain("sql")
		expect(loaded).not.toContain("javascript")
	})

	it("ignores languages the portal does not bundle", async () => {
		const highlighter = await getHighlighter()
		await loadLanguages(highlighter, ["python", "cpp", "", null])
		expect(highlighter.getLoadedLanguages()).not.toContain("python")
	})

	it("canonicalLanguage resolves aliases and rejects the rest", () => {
		expect(canonicalLanguage("PS1")).toBe("powershell")
		expect(canonicalLanguage("bash")).toBe("shellscript")
		expect(canonicalLanguage("yml")).toBe("yaml")
		expect(canonicalLanguage("sql")).toBe("sql")
		expect(canonicalLanguage("python")).toBeNull()
		expect(canonicalLanguage(undefined)).toBeNull()
	})

	it("fencedLanguages reads the languages named on a report's code blocks", () => {
		const markdown = ["# Findings", "```powershell", "Get-Process", "```", "", "~~~ sql", "SELECT 1", "~~~", "```", "no language", "```"].join("\n")
		expect(fencedLanguages(markdown)).toEqual(["powershell", "sql"])
		expect(fencedLanguages("no code here")).toEqual([])
		expect(fencedLanguages(null)).toEqual([])
	})

	it("supportedLanguage: a loaded language (or alias) is kept, anything else is plain text", async () => {
		const highlighter = await getHighlighter()
		await loadLanguages(highlighter, ["yaml"])
		expect(supportedLanguage(highlighter, "yml")).toBe("yaml")
		expect(supportedLanguage(highlighter, "python")).toBe(FALLBACK_LANGUAGE)
		// Bundled but not loaded yet: plain text until loadLanguages has run for it.
		expect(supportedLanguage(highlighter, "lua")).toBe(FALLBACK_LANGUAGE)
	})

	it("highlights a loaded language with the JavaScript regex engine", async () => {
		const highlighter = await getHighlighter()
		await loadLanguages(highlighter, ["powershell"])
		const html = highlighter.codeToHtml("Get-Process -Name svchost", { lang: "powershell", themes: codeThemes })
		expect(html).toContain('class="shiki')
		expect(html.match(/<span style="/g)?.length ?? 0).toBeGreaterThan(2)
	})
})
