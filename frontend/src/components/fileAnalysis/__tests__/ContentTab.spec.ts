import type { InspectorResult } from "@/types/file-analysis"
import { mount } from "@vue/test-utils"
import { beforeEach, describe, expect, it, vi } from "vitest"
import ContentTab from "../tabs/ContentTab.vue"

/**
 * The Content tab shows a sample's own content: what its author wrote. It is shown as text, and in
 * the script's language when its name says it, rather than guessed from the code (#1360).
 */

// What each code block asked the highlighter for; highlighting itself is Shiki's business.
const asked = vi.hoisted(() => [] as { lang?: string; decode?: boolean }[])
vi.mock("@/directives/v-shiki", () => ({
	default: { created: (_el: HTMLElement, binding: { value: { lang?: string; decode?: boolean } }) => asked.push(binding.value) }
}))

function result(filename: string, content: InspectorResult["content"]): InspectorResult {
	return {
		sha256: "a".repeat(64),
		filename,
		customer_code: "ACME",
		filetype: "script",
		magic: "ASCII text",
		extension_mismatch: false,
		entropy: 4,
		hashes: {},
		iocs: { urls: [], ips: [], domains: [] },
		previews: [],
		content,
		flags: [],
		analysis_incomplete: false,
		verdict_hint: "suspicious"
	}
}

beforeEach(() => {
	asked.length = 0
})

describe("file analysis Content tab", () => {
	it("shows a sample's markup as text", () => {
		const raw = '$u = "<img src=x onerror=alert(1)>"\nInvoke-WebRequest $u'
		const wrapper = mount(ContentTab, { props: { result: result("dropper.ps1", { raw, deobfuscated: raw }) } })

		const blocks = wrapper.findAll("pre")
		expect(blocks).toHaveLength(2)
		for (const pre of blocks) {
			expect(pre.text()).toBe(raw)
			expect(pre.element.children).toHaveLength(0)
		}
		expect(wrapper.find("img").exists()).toBe(false)
		expect(asked.every(binding => binding.decode === true)).toBe(true)
	})

	it("highlights a script in the language its name says", () => {
		mount(ContentTab, { props: { result: result("Dropper.PS1", { raw: "iex $a", deobfuscated: "iex $b" }) } })
		expect(asked.map(binding => binding.lang)).toEqual(["powershell", "powershell"])
	})

	it("lets the highlighter guess for a name that says nothing", () => {
		mount(ContentTab, { props: { result: result("sample", { raw: "iex $a" }) } })
		expect(asked[0].lang).toBeUndefined()
	})

	it("names the language of macros, PDF JavaScript and extracted text", () => {
		mount(ContentTab, {
			props: { result: result("invoice.pdf", { macros: "Sub AutoOpen()", javascript: "app.alert(1)", text: "Invoice" }) }
		})
		expect(asked.map(binding => binding.lang)).toEqual(["vb", "javascript", "text"])
	})
})
