import type { CustomerWafInstance } from "@/types/customer-waf"
import { flushPromises, mount } from "@vue/test-utils"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h, nextTick, ref } from "vue"
import CustomerWafBlockDialog from "../CustomerWafBlockDialog.vue"

const block = vi.hoisted(() => vi.fn())
const message = vi.hoisted(() => ({ success: vi.fn(), info: vi.fn(), warning: vi.fn(), error: vi.fn() }))

vi.mock("@/api", () => ({ default: { customerWaf: { block } } }))
vi.mock("naive-ui", async importOriginal => ({
	...(await importOriginal<typeof import("naive-ui")>()),
	useMessage: () => message
}))

const WAF: CustomerWafInstance = {
	id: 1,
	customer_code: "ACME",
	name: "prod",
	api_url: "https://waf:8443",
	token_prefix: "wafst_abc",
	verify_tls: false,
	has_ca_cert: false,
	enabled: true,
	last_verified_at: "2026-09-23T10:00:00",
	last_verified_role: "admin",
	created_by: null,
	created_at: null,
	updated_by: null,
	updated_at: null,
	syslog_host: null,
	syslog_port: null,
	graylog_input_id: null,
	graylog_stream_id: null,
	graylog_index_set_id: null,
	forwarding_provisioned_at: null
}

/** The dialog open on one block-capable WAF, target and reason filled in. */
async function openDialog() {
	const show = ref(false)
	const blocked = vi.fn()
	const wrapper = mount(
		defineComponent({
			setup: () => () =>
				h(CustomerWafBlockDialog, {
					show: show.value,
					"onUpdate:show": (value: boolean) => (show.value = value),
					customerCode: "ACME",
					instances: [WAF],
					initialTarget: "203.0.113.7",
					alertId: 42,
					onBlocked: blocked
				})
		}),
		{ attachTo: document.body }
	)
	show.value = true
	await nextTick()
	await flushPromises()
	return { wrapper, show, blocked }
}

function blockButton() {
	const button = [...document.body.querySelectorAll("button")].find(b => b.textContent?.trim() === "Block")
	if (!button) throw new Error("no Block button")
	return button
}

describe("customerWafBlockDialog", () => {
	beforeEach(() => {
		block.mockReset()
		for (const fn of Object.values(message)) fn.mockReset()
	})

	afterEach(() => {
		document.body.innerHTML = ""
	})

	it("on a new block: a success message, the blocked event, and the dialog closes", async () => {
		block.mockResolvedValue({
			data: { action: "created", target: "203.0.113.7", message: "Blocked 203.0.113.7", warnings: [] }
		})
		const { show, blocked } = await openDialog()

		blockButton().click()
		await flushPromises()

		expect(block).toHaveBeenCalledWith("ACME", 1, {
			target: "203.0.113.7",
			reason: "Responding to alert #42",
			alert_id: 42
		})
		expect(message.success).toHaveBeenCalledWith("Blocked 203.0.113.7")
		expect(blocked).toHaveBeenCalledWith({ wafId: 1, action: "created", target: "203.0.113.7" })
		expect(show.value).toBe(false)
	})

	it("on an address already blocked: an info message, and each warning as its own", async () => {
		block.mockResolvedValue({
			data: {
				action: "already_blocked",
				target: "10.0.0.0/16",
				message: "Already blocked",
				warnings: ["10.0.0.0/16 is not a public address"]
			}
		})
		const { show } = await openDialog()

		blockButton().click()
		await flushPromises()

		expect(message.info).toHaveBeenCalledWith("Already blocked")
		expect(message.success).not.toHaveBeenCalled()
		expect(message.warning).toHaveBeenCalledWith("10.0.0.0/16 is not a public address", { duration: 8000 })
		expect(show.value).toBe(false)
	})

	it("on a failure: the dialog stays open and says why, with no message", async () => {
		block.mockRejectedValue({
			response: { data: { detail: "The WAF rejected the token", reason: "token_rejected" } }
		})
		const { show, blocked } = await openDialog()

		blockButton().click()
		await flushPromises()

		expect(show.value).toBe(true)
		expect(blocked).not.toHaveBeenCalled()
		expect(message.success).not.toHaveBeenCalled()
		expect(document.body.textContent).toContain("The WAF rejected the token")
		expect(document.body.textContent).toContain("Issue a new one in the WAF")
	})
})
