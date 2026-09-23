import type { CustomerWafInstance } from "@/types/customer-waf"
import { flushPromises, mount } from "@vue/test-utils"
import { beforeEach, describe, expect, it, vi } from "vitest"
import CustomerWafForm from "../CustomerWafForm.vue"

const updateInstance = vi.fn()
const createInstance = vi.fn()

vi.mock("@/api", () => ({
	default: { customerWaf: { updateInstance: (...a: unknown[]) => updateInstance(...a), createInstance: (...a: unknown[]) => createInstance(...a) } }
}))

const existing: CustomerWafInstance = {
	id: 7,
	customer_code: "ACME",
	name: "prod",
	api_url: "https://waf:8443",
	token_prefix: "wafst_AbCdEf...",
	verify_tls: false,
	has_ca_cert: false,
	enabled: true,
	last_verified_at: null,
	last_verified_role: "viewer",
	created_by: null,
	created_at: null,
	updated_by: null,
	updated_at: null
}

const ModalStub = { template: "<div><slot /><slot name=\"footer\" /></div>" }

async function open(instance: CustomerWafInstance | null) {
	const w = mount(CustomerWafForm, {
		props: { customerCode: "ACME", instance, show: false },
		global: { stubs: { NModal: ModalStub, Modal: ModalStub } }
	})
	await w.setProps({ show: true })
	return w
}

const tokenInput = (w: Awaited<ReturnType<typeof open>>) => w.find("input[type=password]")

describe("customerWafForm — the service token is write-only", () => {
	beforeEach(() => {
		updateInstance.mockReset().mockResolvedValue({ data: { instance: existing, verification: null, warnings: [] } })
		createInstance.mockReset()
	})

	it("never pre-fills the token when editing; shows the prefix as a hint only", async () => {
		const w = await open(existing)
		const input = tokenInput(w)
		expect((input.element as HTMLInputElement).value).toBe("")
		expect(input.attributes("placeholder")).toContain("wafst_AbCdEf...")
		expect(input.attributes("placeholder")).toContain("leave blank to keep")
	})

	it("saving without touching the token sends a blank token (the backend keeps the stored one)", async () => {
		const w = await open(existing)
		const saveButton = w.findAll("button").find(b => b.text() === "Save")
		expect(saveButton).toBeDefined()
		await saveButton?.trigger("click")
		await flushPromises()
		expect(updateInstance).toHaveBeenCalledTimes(1)
		const payload = updateInstance.mock.calls[0]?.[2]
		expect(payload.service_token).toBe("")
		expect(payload).not.toHaveProperty("ca_cert_pem")
	})

	it("defaults TLS verification to off for a new WAF", async () => {
		const w = await open(null)
		expect(w.text()).toContain("Off by default")
	})
})
