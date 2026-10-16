import { mount } from "@vue/test-utils"
import { afterEach, describe, expect, it } from "vitest"
import TemplateDeleteConfirm from "../TemplateDeleteConfirm.vue"

describe("templateDeleteConfirm", () => {
	let wrapper: ReturnType<typeof mount> | null = null
	afterEach(() => {
		wrapper?.unmount()
		wrapper = null
	})

	it("asks before deleting, with the focus on Cancel so Enter cannot delete", () => {
		wrapper = mount(TemplateDeleteConfirm, { props: { name: "Triage" }, attachTo: document.body })
		expect(wrapper.text()).toContain("Delete “Triage”?")
		expect(wrapper.attributes("role")).toBe("alertdialog")
		expect(document.activeElement?.textContent?.trim()).toBe("Cancel")
	})

	it("confirms, cancels, and cancels on Escape", async () => {
		wrapper = mount(TemplateDeleteConfirm, { props: { name: "Triage" } })
		await wrapper.find("[data-testid=template-delete-confirm-button]").trigger("click")
		await wrapper.find("[data-testid=template-delete-cancel]").trigger("click")
		await wrapper.trigger("keydown", { key: "Escape" })
		expect(wrapper.emitted("confirm")).toHaveLength(1)
		expect(wrapper.emitted("cancel")).toHaveLength(2)
	})

	it("shows the deletion under way", () => {
		wrapper = mount(TemplateDeleteConfirm, { props: { name: "Triage", loading: true } })
		expect(wrapper.find("[data-testid=template-delete-confirm-button]").classes()).toContain("n-button--loading")
	})
})
