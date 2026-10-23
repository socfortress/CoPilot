/**
 * A drawer's markdown through CoPilot's real `Markdown` component (markdown-it, HTML off, images as
 * links): a `javascript:` link is never a live link, raw HTML is text, and no image loads. Shiki is
 * replaced by a highlighter that colours nothing (it isn't what is under test); the image rule is the
 * real one.
 */
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils"
import { afterEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import MemoryDrawerDetail from "../MemoryDrawerDetail.vue"

const getDrawer = vi.fn()

vi.mock("@/api", () => ({
	default: { talonMemory: { getDrawer: (...a: unknown[]) => getDrawer(...a), forgetDrawer: vi.fn() } }
}))
vi.mock("@/utils/highlighter", async importOriginal => {
	const real = await importOriginal<typeof import("@/utils/highlighter")>()
	return {
		...real,
		getHighlighter: async () => ({ getLoadedLanguages: () => [] }),
		markdownItSafeHighlight: () => () => {}
	}
})
vi.mock("@shikijs/markdown-it/core", () => ({ fromHighlighter: () => () => {} }))

const Show = defineComponent({
	props: { show: { type: Boolean, default: false } },
	setup:
		(props, { slots }) =>
		() =>
			props.show ? h("div", [slots.default?.(), slots.footer?.()]) : null
})
const Passthrough = defineComponent({
	setup:
		(_, { slots }) =>
		() =>
			h("div", slots.default?.())
})

const ID = "drawer_ACME_false_positives_0123456789abcdef01234567"
const CONTENT = [
	"# Lesson",
	"",
	"[click me](javascript:alert(1)) and [also](JaVaScRiPt:alert(2)) and [data](data:text/html;base64,PHNjcmlwdD4=)",
	"",
	'<a href="javascript:alert(3)">raw link</a> <img src=x onerror="alert(4)">',
	"",
	"![pixel](https://tracker.invalid/p.png)",
	"",
	"[a real one](https://example.com/advisory)"
].join("\n")

enableAutoUnmount(afterEach)

describe("a drawer's markdown", () => {
	it("renders no javascript: link, no raw HTML and no image", async () => {
		getDrawer.mockResolvedValue({
			data: {
				drawer_id: ID,
				customer_code: "ACME",
				openable: true,
				room: "false_positives",
				source: "review_one_off",
				source_ref: null,
				filed_at: null,
				durable: false,
				testing_hidden: false,
				visible_to_investigations: true,
				preview: null,
				content: CONTENT,
				forgettable: true,
				why_not_forgettable: null,
				why_hidden: null
			}
		})
		const wrapper = mount(MemoryDrawerDetail, {
			props: { customerCode: "ACME", drawerId: ID },
			global: {
				stubs: { Drawer: Show, DrawerContent: Passthrough, Modal: Show, RouterLink: true, Icon: true }
			}
		})
		await flushPromises()
		await flushPromises()
		const content = wrapper.get('[data-testid="talon-memory-detail-content"]')
		expect(content.find("h1").text()).toBe("Lesson")
		const hrefs = content.findAll("a").map(a => a.attributes("href") ?? "")
		expect(hrefs.some(href => /^\s*(?:javascript|data):/i.test(href))).toBe(false)
		expect(hrefs).toContain("https://example.com/advisory")
		expect(content.text()).toContain("click me")
		// Raw HTML is text, never an element; the image is a link, never loaded.
		expect(content.text()).toContain('<a href="javascript:alert(3)">raw link</a>')
		expect(content.find("img").exists()).toBe(false)
	})
})
