/**
 * The approval card (M5-11b): everything it shows comes from `GET /api/talon/actions/{id}`; the
 * model's reason is untrusted text, a comment is raw with its links highlighted and never
 * clickable, provenance is a banner; Approve / Deny follow `can_decide`, Withdraw `is_requester`
 * while pending, a host action asks first naming the host and the customer; a decision in flight
 * disables every button; the backend's texts are text; it polls every 10 s until settled, and not
 * after unmount.
 */
import type { TalonAction } from "@/types/talonActions"
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import {
	knownAction,
	PROVENANCE_INJECTION,
	PROVENANCE_UNTRUSTED,
	PROVENANCE_WEB,
	resetTalonActions,
	TALON_APPROVAL_POLL_MS
} from "../approvals"
import TalonApprovalCard from "../TalonApprovalCard.vue"
import { APPROVAL_ID, axiosError, quarantineAction, response, talonAction } from "./fixtures"

const get = vi.fn()
const approve = vi.fn()
const deny = vi.fn()
const withdraw = vi.fn()

vi.mock("@/api", () => ({
	default: {
		talonActions: {
			get: (...a: unknown[]) => get(...a),
			approve: (...a: unknown[]) => approve(...a),
			deny: (...a: unknown[]) => deny(...a),
			withdraw: (...a: unknown[]) => withdraw(...a)
		}
	}
}))
vi.mock("@/stores/settings", () => ({ useSettingsStore: () => ({ dateFormat: { datetime: "yyyy-MM-dd HH:mm" } }) }))

/** RouterLink without a router: the target as data. */
const RouterLinkStub = defineComponent({
	name: "RouterLink",
	props: { to: { type: Object, required: true } },
	setup:
		(props, { slots }) =>
		() =>
			h("a", { "data-to": JSON.stringify(props.to) }, slots.default?.())
})

/** NModal without teleport or transitions: its content only while shown. */
const ModalStub = defineComponent({
	name: "Modal",
	props: { show: { type: Boolean, default: false } },
	setup:
		(props, { slots }) =>
		() =>
			props.show ? h("div", { "data-testid": "modal-stub" }, [slots.default?.(), slots.footer?.()]) : null
})

const HOSTILE_REASON = `<a href="https://evil.invalid">click</a> <img src=x onerror="alert(1)"> **bold** [x](https://evil.invalid/y) ![x](https://evil.invalid/pixel.png)`

function render() {
	return mount(TalonApprovalCard, {
		props: { approvalId: APPROVAL_ID },
		global: { stubs: { Icon: true, RouterLink: RouterLinkStub, NModal: ModalStub, Modal: ModalStub } }
	})
}

async function mounted(action: TalonAction) {
	get.mockResolvedValueOnce(response(action))
	const wrapper = render()
	await flushPromises()
	return wrapper
}

function button(wrapper: ReturnType<typeof render>, id: string) {
	return wrapper.find(`[data-testid="talon-approval-${id}"]`)
}

function deferred<T>() {
	let resolve: (value: T) => void = () => {}
	const promise = new Promise<T>(r => (resolve = r))
	return { promise, resolve }
}

enableAutoUnmount(afterEach)

describe("talon approval card", () => {
	beforeEach(() => {
		resetTalonActions()
		for (const fn of [get, approve, deny, withdraw]) fn.mockReset()
	})
	afterEach(() => {
		vi.useRealTimers()
	})

	it("reads the proposal by its id and shows the GET's action, target, customer and arguments", async () => {
		const wrapper = await mounted(talonAction())
		expect(get).toHaveBeenCalledWith(APPROVAL_ID, expect.any(AbortSignal))
		expect(wrapper.get('[data-testid="talon-approval-title"]').text()).toBe("Set the alert's status")
		expect(wrapper.get('[data-testid="talon-approval-customer"]').text()).toBe("ACME")
		const link = wrapper.get('[data-testid="talon-approval-alert-link"]')
		expect(link.text()).toBe("Alert #840")
		expect(JSON.parse(link.attributes("data-to") as string)).toEqual({
			name: "IncidentManagement-Alert",
			params: { id: "840" }
		})
		expect(wrapper.get('[data-testid="talon-approval-arg-status"]').text()).toBe("CLOSED")
		expect(wrapper.get('[data-testid="talon-approval-status"]').text()).toBe("Waiting for a decision")
		expect(wrapper.get('[data-testid="talon-approval-requester"]').text()).toBe("Requested by you")
		expect(wrapper.get('[data-testid="talon-approval-expiry"]').text()).toMatch(/^Expires in 3h 59m$/)
		// Remembered for the thread (its composer and its resume).
		expect(knownAction(APPROVAL_ID)?.action?.state).toBe("pending")
	})

	it("a host target shows the host name and the agent id", async () => {
		const wrapper = await mounted(quarantineAction({ is_requester: false, requester_user_id: "12" }))
		expect(wrapper.get('[data-testid="talon-approval-hostname"]').text()).toBe("WIN-DC01")
		expect(wrapper.get('[data-testid="talon-approval-agent"]').text()).toBe("· agent 001")
		expect(wrapper.find('[data-testid="talon-approval-alert-link"]').exists()).toBe(false)
		expect(wrapper.get('[data-testid="talon-approval-requester"]').text()).toBe("Requested by CoPilot user #12")
	})

	it("the model's reason with markup renders as text only, labelled untrusted", async () => {
		const wrapper = await mounted(talonAction({ reason: HOSTILE_REASON }))
		const reason = wrapper.get('[data-testid="talon-approval-reason"]')
		expect(reason.text()).toContain("untrusted")
		expect(wrapper.get('[data-testid="talon-approval-reason-text"]').text()).toBe(HOSTILE_REASON)
		for (const tag of ["a", "img", "strong", "em", "script"]) expect(reason.find(tag).exists()).toBe(false)
		expect(reason.find("[href]").exists()).toBe(false)
		expect(reason.find("[src]").exists()).toBe(false)
	})

	it("a comment is shown raw, its links highlighted but not clickable", async () => {
		const comment =
			"See https://evil.invalid/a?b=1 and www.example.org, or evil.invalid/path — [x](hxxp://bad.example/p) <a href=x>y</a>"
		const wrapper = await mounted(
			talonAction({
				action: "comment_on_alert",
				args: { alert_id: 840, comment },
				links: true
			})
		)
		const shown = wrapper.get('[data-testid="talon-approval-comment"]')
		expect(shown.text()).toContain(comment)
		const links = shown.findAll('[data-testid="talon-approval-comment-link"]').map(l => l.text())
		expect(links).toEqual([
			"https://evil.invalid/a?b=1",
			"www.example.org",
			"evil.invalid/path",
			"hxxp://bad.example/p"
		])
		expect(shown.find("a").exists()).toBe(false)
		expect(shown.find("[href]").exists()).toBe(false)
		for (const link of shown.findAll('[data-testid="talon-approval-comment-link"]')) {
			expect(link.element.tagName).toBe("SPAN")
		}
		expect(wrapper.get('[data-testid="talon-approval-links-note"]').text()).toMatch(/shown, not opened/)
	})

	it.each([
		["injection_detected", PROVENANCE_INJECTION],
		["untrusted_seen", PROVENANCE_UNTRUSTED],
		["web_used", PROVENANCE_WEB]
	])("provenance %s shows its banner", async (flag, text) => {
		const wrapper = await mounted(talonAction({ provenance: { [flag]: true } }))
		const banners = wrapper.findAll('[data-testid="talon-approval-provenance"]')
		expect(banners.map(b => b.attributes("data-flag"))).toEqual([flag])
		expect(banners[0].text()).toBe(text)
	})

	it("no provenance flag, no banner; all three, three banners", async () => {
		const clean = await mounted(talonAction())
		expect(clean.findAll('[data-testid="talon-approval-provenance"]')).toHaveLength(0)
		const flagged = await mounted(
			talonAction({ provenance: { injection_detected: true, untrusted_seen: true, web_used: true } })
		)
		expect(
			flagged.findAll('[data-testid="talon-approval-provenance"]').map(b => b.attributes("data-flag"))
		).toEqual(["injection_detected", "untrusted_seen", "web_used"])
	})

	it.each<[Partial<TalonAction>, string[]]>([
		[{ can_decide: true, is_requester: true }, ["approve", "deny", "withdraw"]],
		[{ can_decide: true, is_requester: false }, ["approve", "deny"]],
		[{ can_decide: false, is_requester: true }, ["withdraw"]],
		[{ can_decide: false, is_requester: false }, []],
		[{ can_decide: false, is_requester: true, state: "executed", talon_status: "executed" }, []],
		[{ can_decide: false, is_requester: true, expired: true }, []]
	])("buttons follow can_decide and is_requester (%o)", async (extra, shown) => {
		const wrapper = await mounted(talonAction(extra))
		for (const id of ["approve", "deny", "withdraw"]) {
			expect(button(wrapper, id).exists(), id).toBe(shown.includes(id))
		}
	})

	it("an alert action is approved at once", async () => {
		const wrapper = await mounted(talonAction())
		approve.mockResolvedValueOnce(
			response(
				talonAction({ state: "executed", talon_status: "executed", can_decide: false }),
				true,
				"Action executed"
			)
		)
		await button(wrapper, "approve").trigger("click")
		await flushPromises()
		expect(approve).toHaveBeenCalledWith(APPROVAL_ID)
		expect(wrapper.find('[data-testid="modal-stub"]').exists()).toBe(false)
		expect(wrapper.get('[data-testid="talon-approval-status"]').text()).toBe("Executed")
	})

	it.each([
		["quarantine_host", "Quarantine"],
		["release_host", "Release"]
	])("%s asks first, naming the host and the customer", async (name, verb) => {
		const wrapper = await mounted(quarantineAction({ action: name }))
		await button(wrapper, "approve").trigger("click")
		expect(approve).not.toHaveBeenCalled()
		const text = wrapper.get('[data-testid="talon-approval-confirm-text"]').text()
		expect(text).toContain(verb)
		expect(text).toContain("WIN-DC01")
		expect(text).toContain("agent 001")
		expect(text).toContain("ACME")

		await wrapper.get('[data-testid="talon-approval-confirm-cancel"]').trigger("click")
		expect(wrapper.find('[data-testid="talon-approval-confirm-text"]').exists()).toBe(false)
		expect(approve).not.toHaveBeenCalled()

		approve.mockResolvedValueOnce(
			response(quarantineAction({ action: name, state: "executed", can_decide: false }))
		)
		await button(wrapper, "approve").trigger("click")
		await wrapper.get('[data-testid="talon-approval-confirm-run"]').trigger("click")
		await flushPromises()
		expect(approve).toHaveBeenCalledTimes(1)
		expect(wrapper.find('[data-testid="talon-approval-confirm-text"]').exists()).toBe(false)
	})

	it("a decision in flight disables every button, and the confirm's too", async () => {
		const wrapper = await mounted(talonAction())
		const answer = deferred<unknown>()
		deny.mockReturnValueOnce(answer.promise)
		await button(wrapper, "deny").trigger("click")
		for (const id of ["approve", "deny", "withdraw"]) {
			expect(button(wrapper, id).attributes("disabled"), id).toBeDefined()
		}
		// A second click while it runs sends nothing more.
		await button(wrapper, "approve").trigger("click")
		await button(wrapper, "withdraw").trigger("click")
		expect(approve).not.toHaveBeenCalled()
		expect(withdraw).not.toHaveBeenCalled()

		answer.resolve(
			response(talonAction({ state: "denied", talon_status: "denied", can_decide: false, is_requester: true }))
		)
		await flushPromises()
		expect(button(wrapper, "approve").exists()).toBe(false)
		expect(wrapper.get('[data-testid="talon-approval-status"]').text()).toBe("Denied")

		const host = await mounted(quarantineAction())
		const run = deferred<unknown>()
		approve.mockReturnValueOnce(run.promise)
		await button(host, "approve").trigger("click")
		await host.get('[data-testid="talon-approval-confirm-run"]').trigger("click")
		expect(host.get('[data-testid="talon-approval-confirm-run"]').attributes("disabled")).toBeDefined()
		expect(host.get('[data-testid="talon-approval-confirm-cancel"]').attributes("disabled")).toBeDefined()
		expect(button(host, "deny").attributes("disabled")).toBeDefined()
		run.resolve(response(quarantineAction({ state: "executed", talon_status: "executed", can_decide: false })))
		await flushPromises()
	})

	it("withdraw is the requester's, while pending", async () => {
		const wrapper = await mounted(talonAction({ can_decide: false }))
		withdraw.mockResolvedValueOnce(
			response(
				talonAction({ can_decide: false, state: "withdrawn", talon_status: "withdrawn" }),
				true,
				"Action withdrawn"
			)
		)
		await button(wrapper, "withdraw").trigger("click")
		await flushPromises()
		expect(withdraw).toHaveBeenCalledWith(APPROVAL_ID)
		expect(wrapper.get('[data-testid="talon-approval-status"]').text()).toBe("Withdrawn")
		expect(button(wrapper, "withdraw").exists()).toBe(false)
	})

	it("the backend's refusal is shown as its text, and the record read again", async () => {
		const wrapper = await mounted(talonAction())
		approve.mockRejectedValueOnce(
			axiosError(409, { success: false, message: "someone else is deciding this action <b>now</b>" })
		)
		get.mockResolvedValueOnce(response(talonAction({ state: "claiming", can_decide: false })))
		await button(wrapper, "approve").trigger("click")
		await flushPromises()
		const error = wrapper.get('[data-testid="talon-approval-error"]')
		expect(error.text()).toBe("someone else is deciding this action <b>now</b>")
		expect(error.find("b").exists()).toBe(false)
		expect(get).toHaveBeenCalledTimes(2)
		expect(wrapper.get('[data-testid="talon-approval-status"]').text()).toBe("Being decided")
	})

	it("a decision CoPilot made but whose run didn't succeed says so, as text", async () => {
		const wrapper = await mounted(talonAction())
		approve.mockResolvedValueOnce(
			response(
				talonAction({
					state: "failed",
					talon_status: "failed",
					can_decide: false,
					decision: "approve",
					approver_username: "alice",
					execution_result: {
						success: false,
						message: "not run: the assignee has no access",
						status_code: null
					},
					state_reason: "not run: the assignee has no access",
					outcome_reported: true
				}),
				false,
				"The action did not succeed"
			)
		)
		await button(wrapper, "approve").trigger("click")
		await flushPromises()
		expect(wrapper.get('[data-testid="talon-approval-note"]').text()).toBe("The action did not succeed")
		expect(wrapper.get('[data-testid="talon-approval-result"]').text()).toBe(
			"Result: not run: the assignee has no access"
		)
		expect(wrapper.find('[data-testid="talon-approval-state-reason"]').exists()).toBe(false)
		expect(wrapper.get('[data-testid="talon-approval-decision"]').text()).toMatch(/^Approved by alice/)
		expect(wrapper.get('[data-testid="talon-approval-reported"]').text()).toBe("Reported to Talon.")
	})

	it("a read the backend refuses shows its text; a 404 is not read again", async () => {
		vi.useFakeTimers()
		get.mockRejectedValueOnce(axiosError(404, { success: false, message: "Action not found" }))
		const wrapper = render()
		await flushPromises()
		expect(wrapper.get('[data-testid="talon-approval-load-error"]').text()).toBe("Action not found")
		expect(knownAction(APPROVAL_ID)?.failed).toBe(true)
		await vi.advanceTimersByTimeAsync(TALON_APPROVAL_POLL_MS * 3)
		expect(get).toHaveBeenCalledTimes(1)
	})

	it("polls every 10 s while open, stops once the record is final", async () => {
		vi.useFakeTimers()
		get.mockResolvedValueOnce(response(talonAction()))
			.mockResolvedValueOnce(
				response(talonAction({ state: "executing", talon_status: "approved", can_decide: false }))
			)
			.mockResolvedValueOnce(
				response(
					talonAction({
						state: "executed",
						talon_status: "approved",
						can_decide: false,
						outcome_reported: false
					})
				)
			)
			.mockResolvedValueOnce(
				response(
					talonAction({
						state: "executed",
						talon_status: "executed",
						can_decide: false,
						outcome_reported: true
					})
				)
			)
		const wrapper = render()
		await flushPromises()
		expect(get).toHaveBeenCalledTimes(1)
		await vi.advanceTimersByTimeAsync(TALON_APPROVAL_POLL_MS - 1)
		expect(get).toHaveBeenCalledTimes(1)
		await vi.advanceTimersByTimeAsync(1)
		expect(get).toHaveBeenCalledTimes(2)
		expect(wrapper.get('[data-testid="talon-approval-status"]').text()).toBe("Running")
		await vi.advanceTimersByTimeAsync(TALON_APPROVAL_POLL_MS)
		// CoPilot ran it, talon-analyst doesn't have the result yet: still read.
		expect(wrapper.get('[data-testid="talon-approval-reported"]').text()).toMatch(/Not reported to Talon yet/)
		await vi.advanceTimersByTimeAsync(TALON_APPROVAL_POLL_MS)
		expect(get).toHaveBeenCalledTimes(4)
		expect(wrapper.get('[data-testid="talon-approval-status"]').text()).toBe("Executed")
		await vi.advanceTimersByTimeAsync(TALON_APPROVAL_POLL_MS * 5)
		expect(get).toHaveBeenCalledTimes(4)
	})

	it.each([["denied"], ["expired"], ["withdrawn"], ["failed"]])("a %s record is not read again", async status => {
		vi.useFakeTimers()
		get.mockResolvedValue(response(talonAction({ state: status, talon_status: status, can_decide: false })))
		render()
		await flushPromises()
		await vi.advanceTimersByTimeAsync(TALON_APPROVAL_POLL_MS * 3)
		expect(get).toHaveBeenCalledTimes(1)
	})

	it("stops polling on unmount, and a read in flight is aborted", async () => {
		vi.useFakeTimers()
		get.mockResolvedValueOnce(response(talonAction()))
		const wrapper = render()
		await flushPromises()
		let signal: AbortSignal | undefined
		get.mockImplementationOnce((_id: string, s: AbortSignal) => {
			signal = s
			return new Promise(() => {})
		})
		await vi.advanceTimersByTimeAsync(TALON_APPROVAL_POLL_MS)
		expect(get).toHaveBeenCalledTimes(2)
		wrapper.unmount()
		expect(signal?.aborted).toBe(true)
		await vi.advanceTimersByTimeAsync(TALON_APPROVAL_POLL_MS * 5)
		expect(get).toHaveBeenCalledTimes(2)
	})

	it("a read started before a decision's answer doesn't overwrite it", async () => {
		vi.useFakeTimers()
		get.mockResolvedValueOnce(response(talonAction()))
		const wrapper = render()
		await flushPromises()
		const stale = deferred<unknown>()
		get.mockReturnValueOnce(stale.promise)
		await vi.advanceTimersByTimeAsync(TALON_APPROVAL_POLL_MS)
		deny.mockResolvedValueOnce(
			response(talonAction({ state: "denied", talon_status: "denied", can_decide: false }))
		)
		await button(wrapper, "deny").trigger("click")
		await flushPromises()
		stale.resolve(response(talonAction()))
		await flushPromises()
		expect(wrapper.get('[data-testid="talon-approval-status"]').text()).toBe("Denied")
	})
})
