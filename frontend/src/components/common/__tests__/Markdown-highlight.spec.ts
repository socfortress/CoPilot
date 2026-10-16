/**
 * `Markdown.vue` with a real Shiki highlighter: a code fence in a language Shiki hasn't loaded
 * (`kql`, `yara`, a typo, an info string like ```<img), or a fence left unclosed, used to throw
 * inside markdown-it's `highlight` and blank the whole message (Talon v1 and v2 alike). Now such a
 * block renders as plain text and the rest of the message stays. And `noImages` keeps
 * `![x](url)` from becoming an `<img>` that loads.
 */
import { flushPromises, mount } from "@vue/test-utils"
import { createHighlighter } from "shiki"
import { createJavaScriptRegexEngine } from "shiki/engine/javascript"
import { describe, expect, it, vi } from "vitest"
import Markdown from "../Markdown.vue"

const highlighter = createHighlighter({
	themes: ["slack-ochin", "aurora-x"],
	langs: ["javascript"],
	engine: createJavaScriptRegexEngine()
})

vi.mock("@/utils/highlighter", async original => ({
	...(await original<typeof import("@/utils/highlighter")>()),
	getHighlighter: () => highlighter
}))

async function render(source: string, props: Record<string, unknown> = {}) {
	const wrapper = mount(Markdown, { props: { source, ...props } })
	await flushPromises()
	await highlighter
	await flushPromises()
	return wrapper
}

describe("markdown: code fences never blank the message", () => {
	it("a loaded language is highlighted", async () => {
		const wrapper = await render("before\n\n```javascript\nconst a = 1\n```\n\nafter")
		expect(wrapper.find("pre.shiki").exists()).toBe(true)
		expect(wrapper.text()).toContain("before")
		expect(wrapper.text()).toContain("const a = 1")
		expect(wrapper.text()).toContain("after")
	})

	it.each(["kql", "yara", "spl", "log", "diff", "ini", "toml", "cmd", "bat", "no-such-language"])(
		"a fence in %s renders as plain text, with the rest of the message",
		async lang => {
			const wrapper = await render(
				`Run this:\n\n\`\`\`${lang}\nSecurityEvent | where EventID == 4625\n\`\`\`\n\nThen check.`
			)
			expect(wrapper.text()).toContain("Run this:")
			expect(wrapper.text()).toContain("SecurityEvent | where EventID == 4625")
			expect(wrapper.text()).toContain("Then check.")
			expect(wrapper.find("pre").exists()).toBe(true)
		}
	)

	it("an unclosed fence renders its code as text", async () => {
		const wrapper = await render("Start\n\n```kql\nDeviceEvents\n| take 10")
		expect(wrapper.text()).toContain("Start")
		expect(wrapper.text()).toContain("DeviceEvents")
		expect(wrapper.text()).toContain("| take 10")
	})

	it("an info string with markup is neither an element nor a lost message", async () => {
		const wrapper = await render('Look:\n\n```<img src=x onerror="alert(1)">\n<b>code</b>\n```\n\nend')
		expect(wrapper.find("img").exists()).toBe(false)
		expect(wrapper.find("b").exists()).toBe(false)
		expect(wrapper.text()).toContain("<b>code</b>")
		expect(wrapper.text()).toContain("end")
	})
})

describe("markdown: noImages", () => {
	it("renders ![x](url) as a link, never an <img>", async () => {
		const wrapper = await render("see ![x](https://attacker.invalid/?q=1) here", { noImages: true })
		expect(wrapper.find("img").exists()).toBe(false)
		expect(wrapper.text()).toContain("see")
	})

	it("without it, images render as before", async () => {
		const wrapper = await render("![x](https://example.invalid/a.png)")
		expect(wrapper.find("img").exists()).toBe(true)
	})
})

describe("markdownItSafeHighlight on its own", () => {
	it("hands an unloaded language on as text, and answers empty (markdown-it escapes) when highlighting throws", async () => {
		const { markdownItSafeHighlight } = await import("@/utils/highlighter")
		const seen: string[] = []
		const md = {
			options: {
				highlight: (_code: string, lang: string) => {
					seen.push(lang)
					if (lang === "boom") throw new Error("boom")
					return `<pre>${lang}</pre>`
				}
			}
		}
		markdownItSafeHighlight({ getLoadedLanguages: () => ["javascript", "boom"] })(md as never)
		const highlight = md.options.highlight as (code: string, lang: string, attrs: string) => string
		expect(highlight("x", "kql", "")).toBe("<pre>text</pre>")
		expect(highlight("x", "javascript", "")).toBe("<pre>javascript</pre>")
		expect(highlight("x", "", "")).toBe("<pre></pre>")
		expect(highlight("x", "boom", "")).toBe("")
		expect(seen).toEqual(["text", "javascript", "", "boom"])
	})
})
