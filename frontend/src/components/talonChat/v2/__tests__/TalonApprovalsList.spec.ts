/**
 * The Approvals tab's list (M5-11b, decision b): the shared pending list (what the user may decide,
 * and their own that wait), "Mine" read when shown, each row opening the card; and the shared list's
 * poll (`useTalonApprovals`): only while watched and the page visible, stopped at logout.
 */
import type { TalonAction } from "@/types/talonActions"
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import {
	noteApprovalsChanged,
	refreshApprovals,
	resetTalonApprovals,
	TALON_APPROVALS_POLL_MS,
	useTalonApprovals,
	watchApprovals
} from "@/composables/useTalonApprovals"
import TalonApprovalsList from "../TalonApprovalsList.vue"
import { quarantineAction, talonAction } from "./fixtures"

const list = vi.fn()

vi.mock("@/api", () => ({
	default: { talonActions: { list: (...a: unknown[]) => list(...a) } }
}))

const CardStub = defineComponent({
	name: "TalonApprovalCard",
	props: { approvalId: { type: String, required: true } },
	emits: ["changed"],
	setup: props => () => h("div", { "data-testid": "card-stub", "data-approval-id": props.approvalId })
})
const ModalStub = defineComponent({
	name: "Modal",
	props: { show: { type: Boolean, default: false } },
	setup:
		(props, { slots }) =>
		() =>
			props.show ? h("div", { "data-testid": "modal-stub" }, slots.default?.()) : null
})

const DECIDE = talonAction({ id: "a-1", is_requester: false, requester_user_id: "12" })
const MINE_PENDING = quarantineAction({ id: "a-2", can_decide: false })
const MINE_DONE = talonAction({ id: "a-3", state: "executed", talon_status: "executed", can_decide: false })

function answer(actions: TalonAction[]) {
	return { data: { success: true, message: `${actions.length} action(s)`, actions } }
}

function setVisibility(state: "visible" | "hidden") {
	Object.defineProperty(document, "visibilityState", { configurable: true, get: () => state })
	document.dispatchEvent(new Event("visibilitychange"))
}

function render() {
	return mount(TalonApprovalsList, {
		global: { stubs: { TalonApprovalCard: CardStub, NModal: ModalStub, Modal: ModalStub } }
	})
}

enableAutoUnmount(afterEach)

describe("talon approvals list", () => {
	beforeEach(() => {
		resetTalonApprovals()
		list.mockReset()
		setVisibility("visible")
	})
	afterEach(() => {
		vi.useRealTimers()
	})

	it("lists the pending proposals with what the user may do, and a row opens the card", async () => {
		list.mockResolvedValue(answer([DECIDE, MINE_PENDING]))
		await refreshApprovals()
		const wrapper = render()
		await flushPromises()

		const rows = wrapper.findAll('[data-testid="talon-approvals-row"]')
		expect(rows.map(r => r.attributes("data-approval-id"))).toEqual(["a-1", "a-2"])
		expect(rows[0].get('[data-testid="talon-approvals-row-action"]').text()).toBe("Set the alert's status")
		expect(rows[0].get('[data-testid="talon-approvals-row-target"]').text()).toBe("alert #840")
		expect(rows[0].find('[data-testid="talon-approvals-row-decide"]').exists()).toBe(true)
		expect(rows[0].find('[data-testid="talon-approvals-row-mine"]').exists()).toBe(false)
		expect(rows[1].get('[data-testid="talon-approvals-row-target"]').text()).toBe("WIN-DC01")
		expect(rows[1].find('[data-testid="talon-approvals-row-decide"]').exists()).toBe(false)
		expect(rows[1].find('[data-testid="talon-approvals-row-mine"]').exists()).toBe(true)

		await rows[1].trigger("click")
		expect(wrapper.get('[data-testid="card-stub"]').attributes("data-approval-id")).toBe("a-2")

		// The card's proposal moved: the pending list is read again.
		const calls = list.mock.calls.length
		wrapper.getComponent(CardStub).vm.$emit("changed", MINE_PENDING)
		await flushPromises()
		expect(list.mock.calls.length).toBe(calls + 1)
	})

	it("'Mine' reads every proposal of the user's when shown", async () => {
		list.mockImplementation(async (scope: string) =>
			scope === "mine" ? answer([MINE_PENDING, MINE_DONE]) : answer([DECIDE])
		)
		await refreshApprovals()
		const wrapper = render()
		await flushPromises()
		await wrapper.get('[data-testid="talon-approvals-scope-mine"]').trigger("click")
		await flushPromises()
		expect(list).toHaveBeenLastCalledWith("mine", expect.any(AbortSignal))
		const rows = wrapper.findAll('[data-testid="talon-approvals-row"]')
		expect(rows.map(r => r.attributes("data-approval-id"))).toEqual(["a-2", "a-3"])
		expect(rows[1].get('[data-testid="talon-approvals-row-status"]').text()).toBe("Executed")
	})

	it("an empty list says so; a refused read shows its text", async () => {
		list.mockResolvedValueOnce(answer([]))
		await refreshApprovals()
		const wrapper = render()
		await flushPromises()
		expect(wrapper.get('[data-testid="talon-approvals-empty"]').text()).toBe("Nothing waits for a decision.")

		list.mockRejectedValueOnce(
			Object.assign(new Error("x"), {
				isAxiosError: true,
				response: { status: 502, data: { message: "Talon request failed" } }
			})
		)
		await wrapper.get('[data-testid="talon-approvals-refresh"]').trigger("click")
		await flushPromises()
		expect(wrapper.get('[data-testid="talon-approvals-error"]').text()).toBe("Talon request failed")
	})
})

describe("the shared pending list", () => {
	beforeEach(() => {
		resetTalonApprovals()
		list.mockReset()
		setVisibility("visible")
	})
	afterEach(() => {
		vi.useRealTimers()
	})

	it("counts what the user may decide, polls while watched and visible, and stops when unwatched", async () => {
		vi.useFakeTimers()
		list.mockResolvedValue(answer([DECIDE, MINE_PENDING]))
		const { count } = useTalonApprovals()
		const stop = watchApprovals()
		await flushPromises()
		expect(list).toHaveBeenCalledTimes(1)
		expect(list).toHaveBeenCalledWith("pending", expect.any(AbortSignal))
		expect(count.value).toBe(1)

		await vi.advanceTimersByTimeAsync(TALON_APPROVALS_POLL_MS)
		expect(list).toHaveBeenCalledTimes(2)

		setVisibility("hidden")
		await vi.advanceTimersByTimeAsync(TALON_APPROVALS_POLL_MS * 3)
		expect(list).toHaveBeenCalledTimes(2)

		setVisibility("visible") // read at once, then on the interval again
		await flushPromises()
		expect(list).toHaveBeenCalledTimes(3)
		await vi.advanceTimersByTimeAsync(TALON_APPROVALS_POLL_MS)
		expect(list).toHaveBeenCalledTimes(4)

		// A card saw a proposal move: read at once.
		noteApprovalsChanged()
		await flushPromises()
		expect(list).toHaveBeenCalledTimes(5)

		stop()
		await vi.advanceTimersByTimeAsync(TALON_APPROVALS_POLL_MS * 3)
		noteApprovalsChanged() // nobody watches: nothing read
		expect(list).toHaveBeenCalledTimes(5)
	})

	it("logout forgets the list and stops the poll; a late answer changes nothing", async () => {
		vi.useFakeTimers()
		let resolve: (value: unknown) => void = () => {}
		list.mockResolvedValueOnce(answer([DECIDE])).mockReturnValueOnce(new Promise(r => (resolve = r)))
		const { count, actions } = useTalonApprovals()
		watchApprovals()
		await flushPromises()
		expect(count.value).toBe(1)
		await vi.advanceTimersByTimeAsync(TALON_APPROVALS_POLL_MS)
		expect(list).toHaveBeenCalledTimes(2)

		resetTalonApprovals() // stores/auth.ts:setLogout
		expect(count.value).toBe(0)
		resolve(answer([DECIDE, talonAction({ id: "a-9" })]))
		await flushPromises()
		expect(actions.value).toEqual([])
		await vi.advanceTimersByTimeAsync(TALON_APPROVALS_POLL_MS * 3)
		expect(list).toHaveBeenCalledTimes(2)
	})
})
