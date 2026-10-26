import { mount } from "@vue/test-utils"
import { describe, expect, it } from "vitest"
import i18n from "@/lang"
import { elapsedLabel } from "@/utils/elapsed"
import { PASSWORD_PROBLEMS, PASSWORD_REQUIREMENTS } from "@/utils/password-policy"
import { passwordProblemMessage, passwordRequirements } from "@/utils/password-policy-messages"
import { statusSelectOptions, workflowStatusLabel } from "@/utils/workflowStatus"
import StatusStrip from "../StatusStrip.vue"
import WaitingOnYouNotice from "../WaitingOnYouNotice.vue"

/** The shared components and helpers follow the user's language (#1310). */
describe("the shared components and helpers in another language", () => {
	it("show the waiting-on-you notice in Italian", () => {
		i18n.global.locale.value = "it"
		const wrapper = mount(WaitingOnYouNotice, { props: { entity: "case" } })
		expect(wrapper.text()).toContain("Il SOC è in attesa di una tua risposta")
		expect(wrapper.text()).toContain("per questo caso")
		expect(wrapper.get("[data-testid=waiting-on-you-reply]").text()).toBe("Rispondi")
	})

	it("name the strip's total and its aria label in Italian", () => {
		i18n.global.locale.value = "it"
		const wrapper = mount(StatusStrip, { props: { total: 0, entity: "Alerts", icon: "carbon:warning-alt", cells: [] } })
		expect(wrapper.get("section").attributes("aria-label")).toBe("Alert per stato")
		expect(wrapper.get("[data-testid=stat-total]").text()).toContain("Alert totali")
	})

	it("translate the status labels when they are read, not when they were imported", () => {
		expect(workflowStatusLabel("PENDING_CUSTOMER")).toBe("Waiting on you")
		i18n.global.locale.value = "it"
		expect(workflowStatusLabel("PENDING_CUSTOMER")).toBe("In attesa di te")
		expect(statusSelectOptions("OPEN").map(option => option.label)).toEqual(["Aperto", "In corso", "Chiuso"])
		expect(elapsedLabel(3900)).toBe("1 h 05 min")
	})

	it("word the password policy as its English source, and translate it", () => {
		for (const [code, text] of Object.entries(PASSWORD_PROBLEMS)) {
			expect(passwordProblemMessage(code as keyof typeof PASSWORD_PROBLEMS)).toBe(text)
		}
		expect(passwordRequirements()).toBe(PASSWORD_REQUIREMENTS)
		i18n.global.locale.value = "it"
		expect(passwordProblemMessage("no_symbol")).toBe("La password deve contenere un simbolo, come ! @ # $ % _ - . o +")
	})
})
