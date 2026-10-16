/**
 * How a v2 message renders: only the assistant's text goes through Markdown (HTML off, as in v1);
 * every other string from talon-analyst or the model (the prompt read back, `errorText`, tool
 * names, tool arguments, the approval status) is text, so markup in it never becomes elements.
 * And a turn renders the same whether it was streamed or read back.
 */
import type { TalonV2ChatMessage } from "@/types/talonV2"
import { mount } from "@vue/test-utils"
import { describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import {
	applyV2Chunk,
	createV2Parser,
	endAssistantMessage,
	fromUIMessage,
	newAssistantMessage
} from "@/api/talonV2Parser"
import TalonV2Message from "../TalonV2Message.vue"

vi.mock("@/stores/settings", () => ({ useSettingsStore: () => ({ dateFormat: { datetime: "yyyy-MM-dd HH:mm" } }) }))

const MarkdownStub = defineComponent({
	name: "Markdown",
	props: { source: { type: String, default: "" }, noImages: { type: Boolean, default: false } },
	setup: props => () => h("div", { class: "markdown-stub" }, props.source)
})

const HOSTILE = `<img src=x onerror="alert(1)"> **bold** [x](https://evil.invalid) <script>alert(2)</script>`

function render(message: TalonV2ChatMessage) {
	return mount(TalonV2Message, {
		props: { message },
		global: { stubs: { Markdown: MarkdownStub, Icon: true } }
	})
}

function expectNoMarkup(wrapper: ReturnType<typeof render>) {
	expect(wrapper.find("img").exists()).toBe(false)
	expect(wrapper.find("script").exists()).toBe(false)
	expect(wrapper.find("strong").exists()).toBe(false)
	expect(wrapper.find("a").exists()).toBe(false)
}

describe("talon v2 message: text only", () => {
	it("an errorText with markup is shown as text", () => {
		const wrapper = render({
			id: "a",
			role: "assistant",
			items: [],
			createdAt: null,
			status: "failed",
			errorText: HOSTILE
		})
		expect(wrapper.get('[data-testid="talon-v2-error"]').text()).toContain(HOSTILE)
		expectNoMarkup(wrapper)
	})

	it("a tool's name, arguments, error and approval status with markup are shown as text", () => {
		const wrapper = render({
			id: "a",
			role: "assistant",
			createdAt: null,
			status: "completed",
			items: [
				{
					kind: "tool",
					toolCallId: "c1",
					name: `<img src=x onerror=alert(3)>`,
					state: "output-error",
					input: { query: HOSTILE, nested: { why: "**really**" } },
					errorText: HOSTILE
				},
				{
					kind: "tool",
					toolCallId: "c2",
					name: "set_alert_status",
					state: "approval-responded",
					input: { reason: "[click](javascript:alert(1))" },
					approval: { id: "ap-1", status: HOSTILE, approved: false }
				}
			]
		})
		const [first, second] = wrapper.findAll('[data-testid="talon-v2-tool"]')
		expect(first.get('[data-testid="talon-v2-tool-name"]').text()).toBe("<img src=x onerror=alert(3)>")
		expect(first.get('[data-testid="talon-v2-tool-error"]').text()).toBe(HOSTILE)
		expect(first.get('[data-testid="talon-v2-tool-input"]').text()).toContain(JSON.stringify(HOSTILE))
		expect(first.get('[data-testid="talon-v2-tool-input"]').text()).toContain('"why": "**really**"')
		expect(second.get('[data-testid="talon-v2-tool-input"]').text()).toContain("[click](javascript:alert(1))")
		expect(second.get('[data-testid="talon-v2-approval-status"]').text()).toBe(`Approval ${HOSTILE}`)
		expectNoMarkup(wrapper)
		// No Markdown anywhere but the assistant's text (there is none here).
		expect(wrapper.findAllComponents(MarkdownStub)).toHaveLength(0)
	})

	it("arguments too long to show are listed by key name only", () => {
		const wrapper = render({
			id: "a",
			role: "assistant",
			createdAt: null,
			status: "completed",
			items: [
				{
					kind: "tool",
					toolCallId: "c1",
					name: "search",
					state: "output-available",
					input: { truncated: true, keys: ["query", "<b>range</b>"] },
					output: { status: "done", spilled: true, returned: 20, total: 340, truncated: true }
				}
			]
		})
		expect(wrapper.get('[data-testid="talon-v2-tool-keys"]').text()).toBe(
			"Too long to show. Keys: query, <b>range</b>"
		)
		expect(wrapper.find("pre").exists()).toBe(false)
		expect(wrapper.find("b").exists()).toBe(false)
		expect(wrapper.get('[data-testid="talon-v2-tool-status"]').text()).toBe(
			"done · 20 of 340 · truncated · spilled"
		)
	})

	it("the user's prompt read back is text, not Markdown", () => {
		const wrapper = render({
			id: "u",
			role: "user",
			createdAt: null,
			status: "completed",
			items: [{ kind: "text", id: "u-text", text: HOSTILE }]
		})
		expect(wrapper.get('[data-testid="talon-v2-user-text"]').text()).toBe(HOSTILE)
		expectNoMarkup(wrapper)
		expect(wrapper.findAllComponents(MarkdownStub)).toHaveLength(0)
	})

	it("the assistant's text goes to the Markdown component, as in v1", () => {
		const wrapper = render({
			id: "a",
			role: "assistant",
			createdAt: null,
			status: "completed",
			items: [{ kind: "text", id: "text-1", text: "**done**" }]
		})
		const markdown = wrapper.findAllComponents(MarkdownStub)
		expect(markdown).toHaveLength(1)
		expect(markdown[0].props("source")).toBe("**done**")
		// A second layer behind talon-analyst's own escaping of `![`: no image is ever fetched.
		expect(markdown[0].props("noImages")).toBe(true)
	})

	it("the approval placeholder says only whether it waits, keyed by its approval id", () => {
		const pending = render({
			id: "a",
			role: "assistant",
			createdAt: null,
			status: "completed",
			items: [
				{
					kind: "tool",
					toolCallId: "call_q",
					name: "set_alert_status",
					state: "approval-requested",
					input: { alert_id: 840 },
					approval: { id: "ap-1", status: "pending" }
				}
			]
		})
		const card = pending.get('[data-testid="talon-v2-approval"]')
		expect(card.attributes("data-approval-id")).toBe("ap-1")
		expect(card.text()).toBe("Approval pending")
		// Nothing to act on here: M5-11b's card decides from CoPilot's own record.
		expect(card.find("button").exists()).toBe(false)

		const decided = render({
			id: "a",
			role: "assistant",
			createdAt: null,
			status: "completed",
			items: [
				{
					kind: "tool",
					toolCallId: "call_q",
					name: "set_alert_status",
					state: "approval-responded",
					approval: { id: "ap-1", status: "executed", approved: true }
				}
			]
		})
		expect(decided.get('[data-testid="talon-v2-approval"]').text()).toBe("Approval executed")
	})

	it("a cut-off turn says so; usage shows the cost as its decimal string", () => {
		const wrapper = render({
			id: "a",
			role: "assistant",
			createdAt: null,
			status: "cut_off",
			items: [{ kind: "text", id: "text-1", text: "part" }],
			usage: {
				input_tokens: 1200,
				output_tokens: 15,
				requests: 1,
				tool_calls: 0,
				context_tokens: 1055,
				cost_usd: "0.000120"
			}
		})
		expect(wrapper.find('[data-testid="talon-v2-cut-off"]').exists()).toBe(true)
		expect(wrapper.get('[data-testid="talon-v2-usage"]').text()).toBe(
			`${(1200).toLocaleString()} in · 15 out · 1 request · 0 tool calls · $0.000120`
		)
	})
})

describe("a turn renders the same streamed or read back", () => {
	it("text, a tool row and the second step's text", () => {
		const streamed = newAssistantMessage("r1-assistant", "2026-10-16T08:00:00+00:00")
		const parser = createV2Parser({ onChunk: chunk => applyV2Chunk(streamed, chunk) })
		const chunks = [
			{ type: "start" },
			{ type: "text-start", id: "text-1" },
			{ type: "text-delta", id: "text-1", delta: "Checking. " },
			{ type: "tool-input-start", toolCallId: "call_1", toolName: "lookup" },
			{ type: "tool-input-available", toolCallId: "call_1", toolName: "lookup", input: { host: "ws-1" } },
			{ type: "tool-output-available", toolCallId: "call_1", output: { status: "done", spilled: false } },
			{ type: "text-start", id: "text-2" },
			{ type: "text-delta", id: "text-2", delta: "Done." },
			{ type: "finish" }
		]
		parser.push(new TextEncoder().encode(chunks.map(c => `data: ${JSON.stringify(c)}\n\n`).join("")))
		endAssistantMessage(streamed, "finished")

		const read = fromUIMessage({
			id: "r1-assistant",
			role: "assistant",
			parts: [
				{ type: "text", text: "Checking. ", state: "done" },
				{
					type: "tool-lookup",
					toolCallId: "call_1",
					state: "output-available",
					input: { host: "ws-1" },
					output: { status: "done", spilled: false }
				},
				{ type: "text", text: "Done.", state: "done" }
			],
			metadata: { created_at: "2026-10-16T08:00:00+00:00", status: "completed" }
		})

		const live = render(streamed)
		const back = render(read as TalonV2ChatMessage)
		expect(back.html()).toBe(live.html())
		expect(live.text()).toContain("lookup")
	})
})
