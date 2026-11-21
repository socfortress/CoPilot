import { flushPromises } from "@vue/test-utils"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { DETECT_SAMPLE_CHARS, MAX_HIGHLIGHT_CHARS, MAX_HIGHLIGHT_LINE } from "@/utils/code-highlight"
import vShiki from "../v-shiki"

/**
 * The highlighter's limits (#1360): language detection and Shiki's tokenizer both slow down with
 * the square of a line's length, so a one-line obfuscated script froze the page for minutes.
 */

const detect = vi.hoisted(() => vi.fn((_code: string, _opts?: unknown) => ({ language: "PowerShell" })))
vi.mock("flourite", () => ({ default: detect }))

const codeToHtml = vi.hoisted(() => vi.fn((_code: string, _opts: Record<string, unknown>) => "<pre class=\"shiki\">done</pre>"))
vi.mock("@/utils/highlighter", () => ({
	codeThemes: { light: "slack-ochin", dark: "aurora-x" },
	getHighlighter: async () => ({ codeToHtml })
}))

/** A block as CodeSource renders it: a <pre> holding the code as text. */
function block(code: string): HTMLElement {
	const el = document.createElement("div")
	const pre = document.createElement("pre")
	pre.textContent = code
	el.appendChild(pre)
	return el
}

async function highlight(el: HTMLElement, value: { lang?: string; decode?: boolean }) {
	await vShiki.created(el, { value })
	await flushPromises()
}

beforeEach(() => {
	detect.mockClear()
	codeToHtml.mockClear()
})

describe("v-shiki", () => {
	it("highlights code, never tokenizing a line past the limit", async () => {
		const el = block("$a = 1")
		await highlight(el, { decode: true })

		expect(codeToHtml).toHaveBeenCalledTimes(1)
		expect(codeToHtml.mock.calls[0][1]).toMatchObject({ tokenizeMaxLineLength: MAX_HIGHLIGHT_LINE })
		expect(el.innerHTML).toBe("<pre class=\"shiki\">done</pre>")
	})

	it("detects the language of a one-line script from its start only", async () => {
		const script = `powershell -c "iex('${"QUJD".repeat(17_500)}')"`
		await highlight(block(script), { decode: true })

		expect(detect).toHaveBeenCalledTimes(1)
		expect(detect.mock.calls[0][0]).toHaveLength(DETECT_SAMPLE_CHARS)
		expect(codeToHtml.mock.calls[0][0]).toBe(script)
	})

	it("doesn't detect a language it is given", async () => {
		await highlight(block("$a = 1"), { lang: "powershell", decode: true })
		expect(detect).not.toHaveBeenCalled()
		expect(codeToHtml.mock.calls[0][1]).toMatchObject({ lang: "powershell" })
	})

	it("leaves code too large to highlight as it was rendered", async () => {
		const code = "x".repeat(MAX_HIGHLIGHT_CHARS + 1)
		const el = block(code)
		await highlight(el, { decode: true })

		expect(detect).not.toHaveBeenCalled()
		expect(codeToHtml).not.toHaveBeenCalled()
		expect(el.querySelector("pre")?.textContent).toBe(code)
	})

	it("highlights plain text as the text it is: markup in it stays text", async () => {
		await highlight(block("<img src=x onerror=alert(1)>"), { decode: true })
		expect(codeToHtml.mock.calls[0][0]).toBe("<img src=x onerror=alert(1)>")
	})
})
