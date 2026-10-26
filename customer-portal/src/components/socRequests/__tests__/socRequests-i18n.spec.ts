import { afterEach, describe, expect, it } from "vitest"
import i18n from "@/lang"
import { filedOn, questionProblem, STATUS_LABELS, targetOptions, URGENCY_LABELS, URGENCY_OPTIONS } from "../askSoc"
import { request } from "./fixtures"

/** "Ask the SOC" (#1305) in the user's language (#1310): the helpers translate when read. */
describe("ask the SOC in another language", () => {
	afterEach(() => {
		i18n.global.locale.value = "en"
	})

	it("reads its labels in Italian, and in English again after a switch", () => {
		i18n.global.locale.value = "it"
		expect(URGENCY_OPTIONS.map(o => o.label)).toEqual(["Bassa", "Normale", "Alta"])
		expect(URGENCY_LABELS.high).toBe("Alta")
		expect(STATUS_LABELS.open).toBe("In attesa del SOC")
		expect(targetOptions(12)[0]?.label).toBe("Aggiungi al caso #12")
		expect(questionProblem("")).toBe("Scrivi la tua domanda per il SOC")
		expect(filedOn(request(1, { case_id: 4 }), "alert")).toBe("Sul caso #4")

		i18n.global.locale.value = "en"
		expect(URGENCY_OPTIONS.map(o => o.label)).toEqual(["Low", "Normal", "High"])
		expect(STATUS_LABELS.answered).toBe("Answered")
	})
})
