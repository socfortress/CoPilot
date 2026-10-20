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
import { collectAction, commandAction, quarantineAction, talonAction } from "./fixtures"

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

	it("a row's untrusted values are isolated, their hidden characters escaped and flagged", async () => {
		const forged = quarantineAction({
			id: "a-7",
			customer_code: "AC\u200BME",
			target: {
				customer_code: "ACME",
				agent_id: "001",
				velociraptor_id: "C.1234567890abcdef",
				hostname: "WIN\u202E-DC01"
			}
		})
		list.mockResolvedValueOnce(answer([forged, DECIDE]))
		await refreshApprovals()
		const wrapper = render()
		await flushPromises()
		const [row, plain] = wrapper.findAll('[data-testid="talon-approvals-row"]')
		expect(row.get('[data-testid="talon-approvals-row-target"]').text()).toBe("WIN⟨U+202E⟩-DC01")
		expect(row.get('[data-testid="talon-approvals-row-customer"]').text()).toBe("AC⟨U+200B⟩ME")
		expect(row.get('[data-testid="talon-approvals-row-target"]').find("bdi").exists()).toBe(true)
		expect(row.find('[data-testid="talon-approvals-row-hidden"]').exists()).toBe(true)
		expect(row.text()).not.toMatch(/[\u200B\u202E]/)
		expect(plain.find('[data-testid="talon-approvals-row-hidden"]').exists()).toBe(false)
	})

	it("a collection and a command show their kind, with the artifact or the shell, and their host", async () => {
		const collection = collectAction({ id: "a-4" })
		const command = commandAction("Get-Process", { id: "a-5" })
		const hidden = collectAction({
			id: "a-6",
			args: {
				hostname: "WIN-DC01",
				artifact_name: "Windows.System.Pslist",
				parameters: { env: [{ key: "ProcessRegex", value: "a\u202Eb" }] }
			}
		})
		list.mockResolvedValueOnce(answer([collection, command, DECIDE, hidden]))
		await refreshApprovals()
		const wrapper = render()
		await flushPromises()
		const [first, second, third, fourth] = wrapper.findAll('[data-testid="talon-approvals-row"]')

		expect(first.get('[data-testid="talon-approvals-row-action"]').text()).toBe("Collect a Velociraptor artifact")
		const kind = first.get('[data-testid="talon-approvals-row-kind"]')
		expect(kind.attributes("data-kind")).toBe("collection")
		expect(kind.text().replace(/\s+/g, " ")).toBe("Collection · Windows.System.Pslist")
		expect(kind.find("bdi").exists()).toBe(true)
		expect(first.get('[data-testid="talon-approvals-row-target"]').text()).toBe("WIN-DC01")

		expect(second.get('[data-testid="talon-approvals-row-action"]').text()).toBe("Run a command on the endpoint")
		expect(second.get('[data-testid="talon-approvals-row-kind"]').attributes("data-kind")).toBe("command")
		expect(second.get('[data-testid="talon-approvals-row-kind"]').text().replace(/\s+/g, " ")).toBe(
			"Command · PowerShell"
		)
		expect(second.get('[data-testid="talon-approvals-row-target"]').text()).toBe("WIN-DC01")
		// The command itself is the card's to show, never the row's.
		expect(second.text()).not.toContain("Get-Process")

		expect(third.find('[data-testid="talon-approvals-row-kind"]').exists()).toBe(false)
		// A hidden character inside a collection's parameters flags the row.
		expect(first.find('[data-testid="talon-approvals-row-hidden"]').exists()).toBe(false)
		expect(fourth.find('[data-testid="talon-approvals-row-hidden"]').exists()).toBe(true)
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
