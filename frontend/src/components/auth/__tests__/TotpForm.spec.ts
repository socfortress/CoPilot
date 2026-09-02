import { mount } from "@vue/test-utils"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h, nextTick, ref } from "vue"

import TotpForm from "../TotpForm.vue"

const verify2fa = vi.fn(() => Promise.resolve())
const push = vi.fn()

vi.mock("naive-ui", async importOriginal => {
	const actual = await importOriginal<typeof import("naive-ui")>()
	return { ...actual, useMessage: () => ({ error: vi.fn(), success: vi.fn(), info: vi.fn(), warning: vi.fn() }) }
})
vi.mock("vue-router", () => ({ useRouter: () => ({ push }) }))
vi.mock("@/stores/auth", () => ({ useAuthStore: () => ({ verify2fa }) }))
vi.mock("@/utils", () => ({ getApiErrorMessage: () => "err" }))

function otpInputs(wrapper: ReturnType<typeof mount>) {
	// the backup-code n-input is also in the DOM (inside a collapse-transition)
	return wrapper.findAll("input").filter(i => i.attributes("autocomplete") === "one-time-code")
}

async function type(input: ReturnType<typeof otpInputs>[number], char: string) {
	await input.setValue(char)
	await nextTick()
}

describe("totpForm OTP field (issue #1095)", () => {
	beforeEach(() => {
		verify2fa.mockClear()
		push.mockClear()
	})

	it("renders 6 OTP boxes that request the numeric keyboard on mobile", () => {
		const wrapper = mount(TotpForm)
		const inputs = otpInputs(wrapper)

		expect(inputs).toHaveLength(6)
		for (const input of inputs) {
			expect(input.attributes("inputmode")).toBe("numeric")
			expect(input.attributes("pattern")).toBe("[0-9]*")
			expect(input.attributes("autocomplete")).toBe("one-time-code")
			expect(input.attributes("type")).toBe("text")
		}
	})

	it("accepts a 6-digit code with a leading zero and submits it verbatim", async () => {
		const wrapper = mount(TotpForm, { props: { twoFaTempToken: "tok" } })
		const inputs = otpInputs(wrapper)

		for (const [i, char] of [..."012345"].entries()) {
			await type(inputs[i], char)
		}

		expect(verify2fa).toHaveBeenCalledTimes(1)
		expect(verify2fa.mock.calls[0][0]).toMatchObject({ code: "012345", temp_token: "tok" })
	})

	it("rejects letters and symbols", async () => {
		const wrapper = mount(TotpForm)
		const inputs = otpInputs(wrapper)

		await type(inputs[0], "A")
		expect((inputs[0].element as HTMLInputElement).value).toBe("")

		await type(inputs[0], "#")
		expect((inputs[0].element as HTMLInputElement).value).toBe("")

		await type(inputs[0], "1")
		expect((inputs[0].element as HTMLInputElement).value).toBe("1")
	})

	it("strips non-digits out of a pasted code", async () => {
		const wrapper = mount(TotpForm)
		const inputs = otpInputs(wrapper)

		const event = new Event("paste", { bubbles: true, cancelable: true }) as ClipboardEvent
		Object.defineProperty(event, "clipboardData", { value: { getData: () => "12A4 56" } })
		inputs[0].element.dispatchEvent(event)
		await nextTick()

		// "12A4 56" -> the "A" and the space are dropped, the 5 digits are kept in order
		const values = otpInputs(wrapper).map(i => (i.element as HTMLInputElement).value)
		expect(values.join("")).toBe("12456")
	})

	it("still wires up the per-box refs (autofocus on mount + auto-advance)", async () => {
		const wrapper = mount(TotpForm, { attachTo: document.body })
		const inputs = otpInputs(wrapper)

		// onMounted -> focusOnChar(0) walks naive-ui's internal inputRefList
		expect(document.activeElement).toBe(inputs[0].element)

		await type(inputs[0], "7")
		expect(document.activeElement).toBe(inputs[1].element)

		wrapper.unmount()
	})

	it("keeps the backup-code field alphanumeric", async () => {
		const wrapper = mount(TotpForm)
		const buttons = wrapper.findAll("button")
		await buttons[buttons.length - 1].trigger("click")
		await nextTick()

		const backup = wrapper.findAll("input").find(i => i.attributes("autocomplete") !== "one-time-code")
		expect(backup).toBeDefined()
		if (!backup) return
		expect(backup.attributes("inputmode")).toBeUndefined()
		await backup.setValue("ABCD1234EF")
		expect((backup.element as HTMLInputElement).value).toBe("ABCD1234EF")
	})

	it("rEGRESSION GUARD: input-props on n-input-otp itself does NOT reach the inputs", async () => {
		const { NInputOtp } = await import("naive-ui")
		const Old = defineComponent({
			setup() {
				const value = ref<string[]>([])
				return () =>
					h(NInputOtp, {
						"value": value.value,
						"onUpdate:value": (v: string[]) => (value.value = v),
						"inputProps": { autocomplete: "one-time-code", inputmode: "numeric" }
					} as never)
			}
		})
		const wrapper = mount(Old)
		const inputs = wrapper.findAll("input")

		expect(inputs).toHaveLength(6)
		// the whole object lands on the root <div> as one stray attribute instead
		expect(inputs[0].attributes("inputmode")).toBeUndefined()
		expect(inputs[0].attributes("autocomplete")).toBeUndefined()
		expect(wrapper.find(".n-input-otp").attributes("inputprops")).toBe("[object Object]")
	})
})
