import { flushPromises, mount } from "@vue/test-utils"
import { describe, expect, it, vi } from "vitest"
import { ref } from "vue"
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
})
