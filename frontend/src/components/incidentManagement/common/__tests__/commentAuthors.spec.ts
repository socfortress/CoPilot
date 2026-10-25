import { flushPromises } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { effectScope, ref } from "vue"
import { useAuthStore } from "@/stores/auth"
import { AuthUserRole } from "@/types/auth"
import { useCommentAuthors } from "../commentAuthors"

const alerts = vi.hoisted(() => ({ getAlertCommentAuthors: vi.fn() }))
const cases = vi.hoisted(() => ({ getCaseCommentAuthors: vi.fn() }))
vi.mock("@/api", () => ({ default: { incidentManagement: { alerts, cases } } }))

function use(entity: "alert" | "case", id = ref(7)) {
	const scope = effectScope()
	const result = scope.run(() => useCommentAuthors(entity, id))
	if (!result) throw new Error("the scope did not run")
	return { ...result, id, scope }
}

beforeEach(() => {
	setActivePinia(createPinia())
	alerts.getAlertCommentAuthors.mockReset()
	cases.getCaseCommentAuthors.mockReset()
})

/** The role of each comment author, for their role badges (#1305). */
describe("comment authors' roles", () => {
	it("are read once for the alert, and again when it changes", async () => {
		alerts.getAlertCommentAuthors.mockResolvedValue({ data: { authors: { jane: "customer_user", ana: "analyst" } } })
		const { roleOf, id } = use("alert")
		await flushPromises()
		expect(alerts.getAlertCommentAuthors).toHaveBeenCalledWith(7)
		expect(roleOf("jane")).toBe("customer_user")
		expect(roleOf("ana")).toBe("analyst")
		expect(roleOf("velociraptor-ingest")).toBeNull()

		id.value = 8
		await flushPromises()
		expect(alerts.getAlertCommentAuthors).toHaveBeenLastCalledWith(8)
	})

	it("are read for a case from the case's route", async () => {
		cases.getCaseCommentAuthors.mockResolvedValue({ data: { authors: { ron: "responder" } } })
		const { roleOf } = use("case")
		await flushPromises()
		expect(cases.getCaseCommentAuthors).toHaveBeenCalledWith(7)
		expect(roleOf("ron")).toBe("responder")
	})

	it("give a comment the signed-in user just wrote their own role, without reading again", async () => {
		alerts.getAlertCommentAuthors.mockResolvedValue({ data: { authors: {} } })
		const auth = useAuthStore()
		vi.spyOn(auth, "userName", "get").mockReturnValue("boss")
		vi.spyOn(auth, "userRole", "get").mockReturnValue(AuthUserRole.Admin)
		const { roleOf } = use("alert")
		await flushPromises()
		expect(roleOf("boss")).toBe("admin")
		expect(alerts.getAlertCommentAuthors).toHaveBeenCalledTimes(1)
	})

	it("leave the badges out when they can't be read", async () => {
		alerts.getAlertCommentAuthors.mockRejectedValue(new Error("403"))
		const { roleOf } = use("alert")
		await flushPromises()
		expect(roleOf("jane")).toBeNull()
		expect(roleOf(null)).toBeNull()
	})
})
