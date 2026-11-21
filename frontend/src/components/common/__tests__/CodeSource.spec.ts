import { flushPromises, mount } from "@vue/test-utils"
import { describe, expect, it, vi } from "vitest"
import { ref } from "vue"
import { MAX_SHOWN_CHARS } from "@/utils/code-highlight"
import CodeSource from "../CodeSource.vue"

const copy = vi.hoisted(() => vi.fn())
vi.mock("@vueuse/core", async importOriginal => ({
	...(await importOriginal<typeof import("@vueuse/core")>()),
	useClipboard: () => ({ copy, copied: ref(false), isSupported: ref(true) })
}))
// Highlighting is Shiki's business; here only what goes into the block matters.
vi.mock("@/directives/v-shiki", () => ({ default: {} }))

const COMMAND = "uba-admin identity-sources add --tenant lab \\\n    --entra-tenant <directory id> < secret.txt"

describe("codeSource", () => {
	it("shows plain-text code as text: a <placeholder> is never parsed as an HTML tag", () => {
		const wrapper = mount(CodeSource, { props: { code: COMMAND, lang: "shellscript", text: true } })
		const pre = wrapper.get("pre")
		expect(pre.element.children).toHaveLength(0)
		expect(pre.text()).toBe(COMMAND)
	})

	it("copies plain-text code exactly as written", async () => {
		const wrapper = mount(CodeSource, { props: { code: COMMAND, text: true } })
		await wrapper.findAll("button")[0].trigger("click")
		await flushPromises()
		expect(copy).toHaveBeenCalledWith(COMMAND)
	})

	it("keeps rendering code as HTML without it, as before", () => {
		const wrapper = mount(CodeSource, { props: { code: "<b>bold</b>" } })
		expect(wrapper.get("pre").find("b").exists()).toBe(true)
	})

	it("shows the start of very large code, and all of it on request (#1360)", async () => {
		const code = `${"A".repeat(MAX_SHOWN_CHARS)}0123456789`
		const wrapper = mount(CodeSource, { props: { code, text: true } })

		expect(wrapper.get("pre").text()).toHaveLength(MAX_SHOWN_CHARS)
		expect(wrapper.get("[data-testid=code-source-cut]").text()).toContain(
			"Showing the first 200,000 of 200,010 characters."
		)

		const showAll = wrapper.findAll("button").find(b => b.text() === "Show all")
		await showAll?.trigger("click")

		expect(wrapper.get("pre").text()).toBe(code)
		expect(wrapper.find("[data-testid=code-source-cut]").exists()).toBe(false)
	})

	it("copies all of very large code, even while showing its start", async () => {
		const code = "B".repeat(MAX_SHOWN_CHARS + 1)
		const wrapper = mount(CodeSource, { props: { code, text: true } })
		await wrapper.findAll("button").find(b => b.text().includes("copy source"))?.trigger("click")
		await flushPromises()
		expect(copy).toHaveBeenLastCalledWith(code)
	})

	it("says nothing about size when everything is shown", () => {
		const wrapper = mount(CodeSource, { props: { code: "$a = 1", text: true } })
		expect(wrapper.find("[data-testid=code-source-cut]").exists()).toBe(false)
	})

	it("wraps long lines only when asked", () => {
		const wrapped = mount(CodeSource, { props: { code: "x", text: true, wrap: true } })
		expect(wrapped.get("pre").element.parentElement?.className).toContain("[&_pre]:whitespace-pre-wrap")

		const scrolled = mount(CodeSource, { props: { code: "x", text: true } })
		expect(scrolled.get("pre").element.parentElement?.className).not.toContain("whitespace-pre-wrap")
	})
})
