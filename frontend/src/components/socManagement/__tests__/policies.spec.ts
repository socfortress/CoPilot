import type { EditablePolicyCell } from "../utils"
import type { PolicyMatrix } from "@/types/soc-management"
import { mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it } from "vitest"
import { defineComponent, h, ref } from "vue"
import PolicyMatrixEditor from "../policies/PolicyMatrixEditor.vue"
import TargetInput from "../policies/TargetInput.vue"
import { buildPolicyPayload, toEditableCells } from "../utils"

beforeEach(() => setActivePinia(createPinia()))

const matrix: PolicyMatrix = {
	customer_code: "ACME",
	cells: [
		{ entity: "alert", severity: "Critical", ack_minutes: 15, resolve_minutes: 240, source: "default" },
		{ entity: "alert", severity: "High", ack_minutes: 10, resolve_minutes: 60, source: "customer" },
		{ entity: "case", severity: "High", ack_minutes: 60, resolve_minutes: 4320, source: "global" }
	]
}

function editor(readonly = false) {
	const original = toEditableCells(matrix)
	const cells = ref<EditablePolicyCell[]>(original.map(cell => ({ ...cell })))
	const Host = defineComponent({
		setup: () => () =>
			h(PolicyMatrixEditor, {
				modelValue: cells.value,
				"onUpdate:modelValue": (value: EditablePolicyCell[]) => {
					cells.value = value
				},
				original,
				scope: "customer",
				readonly
			})
	})
	return { wrapper: mount(Host), cells }
}

function cell(cells: EditablePolicyCell[], entity: string, severity: string) {
	return cells.find(c => c.entity === entity && c.severity === severity) as EditablePolicyCell
}

describe("policyMatrixEditor", () => {
	it("renders a row per stored cell, labelled with what it inherits from", () => {
		const { wrapper } = editor()
		expect(wrapper.find("[data-testid=policy-row-alert-High]").exists()).toBe(true)
		expect(wrapper.get("[data-testid=policy-own-alert-High]").text()).toContain("Override")
		expect(wrapper.get("[data-testid=policy-own-case-High]").text()).toContain("Global")
		expect(wrapper.get("[data-testid=policy-own-alert-Critical]").text()).toContain("Default")
	})

	it("switching a cell to its own value starts from what it showed, and back to inherit drops it", async () => {
		const { wrapper, cells } = editor()
		await wrapper.get("[data-testid=policy-own-case-High]").trigger("click")
		expect(cell(cells.value, "case", "High")).toMatchObject({
			inherit: false,
			ack_minutes: 60,
			resolve_minutes: 4320
		})

		await wrapper.get("[data-testid=policy-own-alert-High]").trigger("click")
		expect(cell(cells.value, "alert", "High").inherit).toBe(true)
		const payload = buildPolicyPayload(cells.value, "ACME", false)
		expect(payload.cells.find(c => c.severity === "High" && c.entity === "alert")).toMatchObject({
			inherit: true,
			ack_minutes: null,
			resolve_minutes: null
		})
	})

	it("flags a response target longer than the resolution target", async () => {
		const { wrapper, cells } = editor()
		cells.value = cells.value.map(c =>
			c.entity === "alert" && c.severity === "High" ? { ...c, ack_minutes: 600 } : c
		)
		await wrapper.vm.$nextTick()
		expect(wrapper.get("[data-testid=policy-row-alert-High]").text()).toContain("longer than the resolution target")
	})

	it("is read-only for analysts", () => {
		const { wrapper } = editor(true)
		const switchEl = wrapper.get("[data-testid=policy-own-alert-High]")
		expect(switchEl.classes().join(" ")).toContain("disabled")
		expect(wrapper.findAll("input").every(input => (input.element as HTMLInputElement).disabled)).toBe(true)
	})
})

describe("targetInput", () => {
	function input(minutes: number | null) {
		const model = ref<number | null>(minutes)
		const Host = defineComponent({
			setup: () => () =>
				h(TargetInput, {
					modelValue: model.value,
					"onUpdate:modelValue": (value: number | null) => {
						model.value = value
					},
					testId: "target"
				})
		})
		return { wrapper: mount(Host), model }
	}

	it("shows minutes in the largest exact unit", () => {
		const { wrapper } = input(4320)
		expect((wrapper.get("input").element as HTMLInputElement).value).toBe("3")
		expect(wrapper.text()).toContain("d")
	})

	it("writes minutes back from amount × unit, and an empty amount means no target", async () => {
		const { wrapper, model } = input(120)
		const field = wrapper.get("input")
		await field.setValue("1.5")
		await field.trigger("blur")
		expect(model.value).toBe(90)
		await field.setValue("")
		await field.trigger("blur")
		expect(model.value).toBeNull()
	})
})

describe("policyMatrixEditor scope changes", () => {
	it("relabels the cells when the same editor switches from global to a customer", async () => {
		const original = toEditableCells(matrix)
		const wrapper = mount(PolicyMatrixEditor, { props: { modelValue: original, original, scope: "global" } })
		expect(wrapper.get("[data-testid=policy-own-alert-High]").text()).toContain("Custom")
		await wrapper.setProps({ scope: "customer" })
		expect(wrapper.get("[data-testid=policy-own-alert-High]").text()).toContain("Override")
	})
})
