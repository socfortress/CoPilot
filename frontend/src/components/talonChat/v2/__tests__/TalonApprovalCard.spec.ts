/**
 * The approval card (M5-11b, and the review of #1270): everything it shows comes from `GET
 * /api/talon/actions/{id}`; every value is text inside `<bdi>`, invisible and direction-changing
 * characters escaped with a warning; the reason is untrusted text; a comment is raw in a capped box
 * with its links highlighted, never clickable; provenance is a banner. Approve / Deny follow
 * `can_decide`, Withdraw `is_requester` while pending; every Approve confirms, naming the action,
 * target and customer from the record, which the button row shows too. A decision in flight
 * disables the buttons of every card of the proposal; a lost answer says so until a read shows what
 * happened; a confirm closes when the record moves on; a 404 hides the old record.
 *
 * Endpoint actions (talon-analyst's endpoint actions plan, EA-4): a command is a `<pre>` of text
 * nodes, whole, its counts shown and its tabs and trailing spaces marked, never markup, Markdown or
 * links; its shell, shape and risk labels; a collection's parameters as a table; the new provenance
 * banners; the confirm names the host and the command's first line.
 */
import type { TalonAction } from "@/types/talonActions"
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import { DECISION_LOST, knownAction, resetTalonActions, TALON_CARDS_FAST_MS } from "../actionCards"
import {
	HIDDEN_CHARS_WARNING,
	PROVENANCE_COPIED,
	PROVENANCE_ENDPOINT_OUTPUT,
	PROVENANCE_INJECTION,
	PROVENANCE_UNTRUSTED,
	PROVENANCE_WEB,
	RISK_LABELS_NOTE
} from "../approvals"
import TalonApprovalCard from "../TalonApprovalCard.vue"
import {
	APPROVAL_ID,
	axiosError,
	collectAction,
	commandAction,
	listOf,
	quarantineAction,
	response,
	talonAction
} from "./fixtures"

const get = vi.fn()
const list = vi.fn()
const approve = vi.fn()
const deny = vi.fn()
const withdraw = vi.fn()

vi.mock("@/api", () => ({
	default: {
		talonActions: {
			get: (...a: unknown[]) => get(...a),
			list: (...a: unknown[]) => list(...a),
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

const RLO = "\u202E"
const HOSTILE_REASON = `<a href="https://evil.invalid">click</a> <img src=x onerror="alert(1)"> **bold** [x](https://evil.invalid/y) ![x](https://evil.invalid/pixel.png)`

function render() {
	return mount(TalonApprovalCard, {
		props: { approvalId: APPROVAL_ID },
		global: { stubs: { Icon: true, RouterLink: RouterLinkStub, NModal: ModalStub, Modal: ModalStub } }
	})
}

type Wrapper = ReturnType<typeof render>

async function mounted(action: TalonAction) {
	get.mockResolvedValueOnce(response(action))
	const wrapper = render()
	await flushPromises()
	return wrapper
}

function find(wrapper: Wrapper, id: string) {
	return wrapper.find(`[data-testid="talon-approval-${id}"]`)
}

function deferred<T>() {
	let resolve: (value: T) => void = () => {}
	const promise = new Promise<T>(res => (resolve = res))
	return { promise, resolve }
}

async function approveAndConfirm(wrapper: Wrapper) {
	await find(wrapper, "approve").trigger("click")
	await find(wrapper, "confirm-run").trigger("click")
}

enableAutoUnmount(afterEach)

describe("talon approval card", () => {
	beforeEach(() => {
		resetTalonActions()
		for (const fn of [get, list, approve, deny, withdraw]) fn.mockReset()
		list.mockResolvedValue(listOf([]))
	})
	afterEach(() => {
		vi.useRealTimers()
	})

	it("reads the proposal by its id and shows the GET's action, target, customer and arguments", async () => {
		const wrapper = await mounted(talonAction())
		expect(get).toHaveBeenCalledWith(APPROVAL_ID, expect.any(AbortSignal))
		expect(find(wrapper, "title").text()).toBe("Set the alert's status")
		expect(find(wrapper, "customer").text()).toBe("ACME")
		const link = find(wrapper, "alert-link")
		expect(link.text()).toBe("Alert #840")
		expect(JSON.parse(link.attributes("data-to") as string)).toEqual({
			name: "IncidentManagement-Alert",
			params: { id: "840" }
		})
		expect(find(wrapper, "arg-status").text()).toBe("CLOSED")
		expect(find(wrapper, "status").text()).toBe("Waiting for a decision")
		expect(find(wrapper, "requester").text()).toBe("Requested by you")
		expect(find(wrapper, "expiry").text()).toBe("Expires in 4h 0m")
		expect(find(wrapper, "hidden-chars").exists()).toBe(false)
		expect(knownAction(APPROVAL_ID)?.action?.state).toBe("pending")
	})

	it("another requester is named by their CoPilot user name, or their id when gone", async () => {
		const named = await mounted(talonAction({ is_requester: false, requester_username: "bob" }))
		expect(find(named, "requester").text()).toBe("Requested by bob")
		named.unmount()
		resetTalonActions()
		const orphan = await mounted(
			talonAction({ is_requester: false, requester_username: null, requester_user_id: "12" })
		)
		expect(find(orphan, "requester").text()).toBe("Requested by CoPilot user #12")
	})

	it("a host target shows the host name and the agent id", async () => {
		const wrapper = await mounted(quarantineAction())
		expect(find(wrapper, "hostname").text()).toBe("WIN-DC01")
		expect(find(wrapper, "agent").text()).toBe("· agent 001")
		expect(find(wrapper, "alert-link").exists()).toBe(false)
	})

	it("the model's reason with markup renders as text only, labelled untrusted", async () => {
		const wrapper = await mounted(talonAction({ reason: HOSTILE_REASON }))
		const reason = find(wrapper, "reason")
		expect(reason.text()).toContain("untrusted")
		expect(find(wrapper, "reason-text").text()).toBe(HOSTILE_REASON)
		for (const tag of ["a", "img", "strong", "em", "script"]) expect(reason.find(tag).exists()).toBe(false)
		expect(reason.find("[href]").exists()).toBe(false)
		expect(reason.find("[src]").exists()).toBe(false)
	})

	it("every value from the record is isolated in <bdi>", async () => {
		const wrapper = await mounted(
			talonAction({ action: "comment_on_alert", args: { alert_id: 840, comment: "hi" } })
		)
		for (const id of ["customer", "reason-text", "comment-text", "arg-alert_id", "summary"]) {
			expect(find(wrapper, id).find("bdi").exists(), id).toBe(true)
		}
	})

	it("a comment is shown raw in a capped box, its links highlighted but not clickable", async () => {
		const comment =
			"See https://evil.invalid/a?b=1 and www.example.org, or evil.invalid/path — [x](hxxp://bad.example/p) <a href=x>y</a>"
		const wrapper = await mounted(
			talonAction({ action: "comment_on_alert", args: { alert_id: 840, comment }, links: true })
		)
		const block = find(wrapper, "comment")
		expect(block.text()).toContain("Comment text (from the model, posted as written)")
		const box = find(wrapper, "comment-text")
		expect(box.text()).toBe(comment)
		expect(box.classes()).toEqual(expect.arrayContaining(["max-h-60", "overflow-auto"]))
		const links = box.findAll('[data-testid="talon-untrusted-link"]')
		expect(links.map(l => l.text())).toEqual([
			"https://evil.invalid/a?b=1",
			"www.example.org",
			"evil.invalid/path",
			"hxxp://bad.example/p"
		])
		for (const l of links) expect(l.element.tagName).toBe("SPAN")
		expect(block.find("a").exists()).toBe(false)
		expect(block.find("[href]").exists()).toBe(false)
		expect(find(wrapper, "links-note").text()).toMatch(/shown, not opened/)
		// The comment is shown once, in its box: the arguments only point to it.
		expect(find(wrapper, "arg-comment").text()).toBe("shown below")
	})

	it("a bidi override can't forge a link: it is escaped, with a warning", async () => {
		const forged = `https://evil.invalid/${RLO}moc.tfosorcim.www//:sptth`
		const wrapper = await mounted(
			talonAction({ action: "comment_on_alert", args: { alert_id: 840, comment: forged } })
		)
		const box = find(wrapper, "comment-text")
		expect(box.text()).not.toContain(RLO)
		expect(box.text()).toContain("⟨U+202E⟩")
		expect(box.findAll('[data-testid="talon-untrusted-link"]')[0].text()).toBe("https://evil.invalid/")
		expect(find(wrapper, "hidden-chars").text()).toBe(HIDDEN_CHARS_WARNING)
	})

	it("hidden characters are escaped in every value: host, customer, reason, CoPilot's texts, the dialog", async () => {
		const zw = "\u200B"
		const wrapper = await mounted(
			quarantineAction({
				customer_code: `AC${zw}ME`,
				reason: `fine${RLO}enif`,
				target: {
					customer_code: "ACME",
					agent_id: `0${zw}01`,
					velociraptor_id: "C.1234567890abcdef",
					hostname: `WIN${RLO}-DC01`
				},
				state_reason: `odd${zw}`
			})
		)
		expect(find(wrapper, "hidden-chars").exists()).toBe(true)
		expect(find(wrapper, "customer").text()).toBe("AC⟨U+200B⟩ME")
		expect(find(wrapper, "hostname").text()).toBe("WIN⟨U+202E⟩-DC01")
		expect(find(wrapper, "agent").text()).toBe("· agent 0⟨U+200B⟩01")
		expect(find(wrapper, "reason-text").text()).toBe("fine⟨U+202E⟩enif")
		expect(find(wrapper, "state-reason").text()).toBe("odd⟨U+200B⟩")
		expect(wrapper.text()).not.toMatch(/[\u200B\u202E]/)
		await find(wrapper, "approve").trigger("click")
		expect(find(wrapper, "confirm-text").text()).toContain("WIN⟨U+202E⟩-DC01")
		expect(find(wrapper, "confirm-text").text()).not.toMatch(/[\u200B\u202E]/)
		expect(find(wrapper, "approve").attributes("aria-label")).not.toMatch(/[\u200B\u202E]/)
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
			expect(find(wrapper, id).exists(), id).toBe(shown.includes(id))
		}
	})

	it.each<[string, Partial<TalonAction>, string]>([
		["set_alert_status", {}, "Approve: set Alert #840 to CLOSED for customer ACME"],
		[
			"assign_alert",
			{ args: { alert_id: 840, assigned_to: "bob" } },
			"Approve: assign Alert #840 to bob for customer ACME"
		],
		[
			"comment_on_alert",
			{ args: { alert_id: 840, comment: "x" } },
			"Approve: comment on Alert #840 for customer ACME"
		]
	])("every Approve confirms first (%s), naming the action, target and customer", async (name, extra, summary) => {
		const wrapper = await mounted(talonAction({ action: name, ...extra }))
		expect(find(wrapper, "summary").text()).toBe(summary)
		expect(find(wrapper, "approve").attributes("aria-label")).toBe(summary)
		await find(wrapper, "approve").trigger("click")
		expect(approve).not.toHaveBeenCalled()
		expect(find(wrapper, "confirm-text").text()).toContain(summary)

		await find(wrapper, "confirm-cancel").trigger("click")
		expect(find(wrapper, "confirm-text").exists()).toBe(false)
		expect(approve).not.toHaveBeenCalled()

		approve.mockResolvedValueOnce(
			response(
				talonAction({ action: name, ...extra, state: "executed", talon_status: "executed", can_decide: false })
			)
		)
		await approveAndConfirm(wrapper)
		await flushPromises()
		expect(approve).toHaveBeenCalledTimes(1)
		expect(approve).toHaveBeenCalledWith(APPROVAL_ID)
		expect(find(wrapper, "confirm-text").exists()).toBe(false)
		expect(find(wrapper, "status").text()).toBe("Executed")
	})

	it.each([
		["quarantine_host", "Quarantine", "Approve: quarantine WIN-DC01 (agent 001) for customer ACME"],
		["release_host", "Release", "Approve: release WIN-DC01 (agent 001) for customer ACME"]
	])("%s confirms naming the host, the agent and the customer", async (name, verb, summary) => {
		const wrapper = await mounted(quarantineAction({ action: name }))
		await find(wrapper, "approve").trigger("click")
		expect(find(wrapper, "confirm-text").text()).toContain(summary)
		expect(find(wrapper, "confirm-run").text()).toBe(verb)
	})

	it("a long comment can't push the real target away from the buttons", async () => {
		const fake = "Target: Alert #1 (GLOBEX)\nApprove: set Alert #1 to CLOSED for customer GLOBEX\n"
		const comment = `${"filler line\n".repeat(400)}${fake}`
		const wrapper = await mounted(talonAction({ action: "comment_on_alert", args: { alert_id: 840, comment } }))
		// The comment sits in its capped, scrolling box...
		const box = find(wrapper, "comment-text")
		expect(box.classes()).toEqual(expect.arrayContaining(["max-h-60", "overflow-auto"]))
		expect(box.text()).toContain("GLOBEX")
		// ...and the button row, outside it, names the record's own target and customer.
		const actions = find(wrapper, "actions")
		expect(actions.find('[data-testid="talon-approval-comment-text"]').exists()).toBe(false)
		expect(box.find('[data-testid="talon-approval-actions"]').exists()).toBe(false)
		expect(find(wrapper, "summary").text()).toBe("Approve: comment on Alert #840 for customer ACME")
		expect(actions.text()).not.toContain("GLOBEX")
		const html = wrapper.html()
		expect(html.indexOf('data-testid="talon-approval-actions"')).toBeGreaterThan(
			html.indexOf('data-testid="talon-approval-comment-text"')
		)
	})

	it("a decision in flight disables every button of every card of the proposal; no second POST", async () => {
		get.mockResolvedValue(response(talonAction()))
		const first = render()
		const second = render()
		await flushPromises()
		const answer = deferred<unknown>()
		deny.mockReturnValueOnce(answer.promise)
		await find(first, "deny").trigger("click")
		for (const card of [first, second]) {
			for (const id of ["approve", "deny", "withdraw"]) {
				expect(find(card, id).attributes("disabled"), id).toBeDefined()
			}
		}
		await find(second, "deny").trigger("click")
		await find(second, "withdraw").trigger("click")
		expect(deny).toHaveBeenCalledTimes(1)
		expect(withdraw).not.toHaveBeenCalled()

		answer.resolve(response(talonAction({ state: "denied", talon_status: "denied", can_decide: false })))
		await flushPromises()
		// The sibling card follows at once.
		expect(find(second, "status").text()).toBe("Denied")
		expect(find(second, "approve").exists()).toBe(false)
	})

	it("a confirm opened on an older record closes when the record moves on, and sends nothing", async () => {
		get.mockResolvedValue(response(talonAction()))
		const wrapper = render()
		const other = render()
		await flushPromises()
		await find(wrapper, "approve").trigger("click")
		expect(find(wrapper, "confirm-run").exists()).toBe(true)
		// Decided from the other card meanwhile.
		deny.mockResolvedValueOnce(
			response(talonAction({ state: "denied", talon_status: "denied", can_decide: false }))
		)
		await find(other, "deny").trigger("click")
		await flushPromises()
		expect(find(wrapper, "confirm-run").exists()).toBe(false)
		expect(approve).not.toHaveBeenCalled()
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
		await find(wrapper, "withdraw").trigger("click")
		await flushPromises()
		expect(withdraw).toHaveBeenCalledWith(APPROVAL_ID)
		expect(find(wrapper, "status").text()).toBe("Withdrawn")
		expect(find(wrapper, "withdraw").exists()).toBe(false)
	})

	it("the backend's refusal is shown as its text, and the record read again", async () => {
		const wrapper = await mounted(talonAction())
		approve.mockRejectedValueOnce(
			axiosError(409, { success: false, message: "someone else is deciding this action <b>now</b>" })
		)
		get.mockResolvedValueOnce(response(talonAction({ state: "claiming", can_decide: false })))
		await approveAndConfirm(wrapper)
		await flushPromises()
		const error = find(wrapper, "error")
		expect(error.text()).toBe("someone else is deciding this action <b>now</b>")
		expect(error.find("b").exists()).toBe(false)
		expect(get).toHaveBeenCalledTimes(2)
		expect(find(wrapper, "status").text()).toBe("Being decided")
	})

	it.each([[502], [504], [null]])(
		"an approve whose answer is lost (%s) says so, until a read shows the outcome",
		async status => {
			vi.useFakeTimers()
			const wrapper = await mounted(talonAction())
			approve.mockRejectedValueOnce(
				status === null
					? Object.assign(new Error("Network Error"), { isAxiosError: true })
					: axiosError(status, "<html>")
			)
			// The first read after: still running; the next: run.
			get.mockResolvedValueOnce(
				response(talonAction({ state: "executing", talon_status: "approved", can_decide: false }))
			).mockResolvedValue(
				response(talonAction({ state: "executed", talon_status: "executed", can_decide: false }))
			)
			list.mockResolvedValue(
				listOf([talonAction({ state: "executed", talon_status: "executed", can_decide: false })])
			)
			await approveAndConfirm(wrapper)
			await flushPromises()
			expect(find(wrapper, "error").text()).toBe(DECISION_LOST)
			expect(find(wrapper, "status").text()).toBe("Running")
			await vi.advanceTimersByTimeAsync(TALON_CARDS_FAST_MS)
			await flushPromises()
			expect(find(wrapper, "status").text()).toBe("Executed")
			expect(find(wrapper, "error").exists()).toBe(false)
		}
	)

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
		await approveAndConfirm(wrapper)
		await flushPromises()
		expect(find(wrapper, "note").text()).toBe("The action did not succeed")
		expect(find(wrapper, "result").text()).toBe("Result: not run: the assignee has no access")
		expect(find(wrapper, "state-reason").exists()).toBe(false)
		expect(find(wrapper, "decision").text()).toMatch(/^Approved by alice/)
		expect(find(wrapper, "reported").text()).toBe("Reported to Talon.")
	})

	it("a 404 after a good read hides the old record and its buttons", async () => {
		vi.useFakeTimers()
		const wrapper = await mounted(talonAction())
		expect(find(wrapper, "approve").exists()).toBe(true)
		// The row moved; reading it again, the user may no longer see it.
		list.mockResolvedValue(listOf([talonAction({ can_decide: false })]))
		get.mockRejectedValueOnce(axiosError(404, { success: false, message: "Action not found" }))
		await vi.advanceTimersByTimeAsync(TALON_CARDS_FAST_MS)
		await flushPromises()
		expect(find(wrapper, "load-error").text()).toBe("Action not found")
		for (const id of ["approve", "deny", "withdraw", "customer", "alert-link"]) {
			expect(find(wrapper, id).exists(), id).toBe(false)
		}
		expect(knownAction(APPROVAL_ID)?.gone).toBe(true)
	})

	it("the expiry counts down from CoPilot's seconds left; unknown when unreadable", async () => {
		vi.useFakeTimers()
		const wrapper = await mounted(talonAction({ expires_in_seconds: 125, expires_at: "1999-01-01T00:00:00" }))
		expect(find(wrapper, "expiry").text()).toBe("Expires in 2m 5s")
		await vi.advanceTimersByTimeAsync(5_000)
		expect(find(wrapper, "expiry").text()).toBe("Expires in 2m 0s")
		await vi.advanceTimersByTimeAsync(121_000)
		expect(find(wrapper, "expiry").text()).toBe("Expired")
		wrapper.unmount()

		resetTalonActions()
		const unknown = await mounted(talonAction({ expires_in_seconds: undefined, expires_at: "not a time" }))
		expect(find(unknown, "expiry").text()).toBe("Expiry unknown")
	})
})

/** 40 lines: markup, Markdown, a link, a URL, a tab, and trailing spaces on six of them. */
const HOSTILE_COMMAND = [
	"<script>alert(1)</script>",
	"Get-Process | Select-Object -First 50 **bold**   ",
	"# [x](https://evil.invalid/y) and https://evil.invalid/a?b=1  ",
	"\tWrite-Output 'tabbed'",
	'<img src=x onerror="alert(1)"> <a href="https://evil.invalid">click</a>',
	...Array.from({ length: 35 }, (_, i) => `Get-Service -Name svc${i + 1}${i % 10 === 0 ? " " : ""}`)
].join("\n")

describe("talon approval card: endpoint collections and commands", () => {
	beforeEach(() => {
		resetTalonActions()
		for (const fn of [get, list, approve, deny, withdraw]) fn.mockReset()
		list.mockResolvedValue(listOf([]))
	})

	it("a command with markup, Markdown, links, 40 lines and trailing spaces renders as literal text, whole", async () => {
		expect(HOSTILE_COMMAND.split("\n")).toHaveLength(40)
		const wrapper = await mounted(commandAction(HOSTILE_COMMAND))
		expect(find(wrapper, "title").text()).toBe("Run a command on the endpoint")

		const pre = find(wrapper, "command-text")
		expect(pre.element.tagName).toBe("PRE")
		// Every character, every line, in order: the box's text is the command.
		expect(pre.element.textContent).toBe(HOSTILE_COMMAND)
		expect(pre.element.innerHTML).toContain("&lt;script&gt;alert(1)&lt;/script&gt;")
		for (const tag of ["script", "img", "a", "strong", "em", "code", "p", "ul", "li"]) {
			expect(pre.find(tag).exists(), tag).toBe(false)
		}
		expect(pre.find("[href]").exists()).toBe(false)
		expect(pre.find("[src]").exists()).toBe(false)
		expect(pre.find('[data-testid="talon-untrusted-link"]').exists()).toBe(false)
		// Text nodes and the whitespace markers only.
		expect(pre.findAll("*").every(el => el.element.tagName === "SPAN")).toBe(true)
		// Scrolled within a fixed height, never wrapped.
		expect(pre.classes()).toEqual(expect.arrayContaining(["whitespace-pre", "overflow-auto", "max-h-80"]))

		const trailing = pre.findAll('[data-testid="talon-command-trailing"]')
		expect(trailing.map(el => el.element.textContent)).toEqual(["   ", "  ", " ", " ", " ", " "])
		const tabs = pre.findAll('[data-testid="talon-command-tab"]')
		expect(tabs.map(el => el.element.textContent)).toEqual(["\t"])

		expect(find(wrapper, "command-counts").text()).toBe(
			`40 lines, ${HOSTILE_COMMAND.length.toLocaleString("en-US")} characters`
		)
		expect(find(wrapper, "whitespace").text()).toBe(
			"Whitespace: 1 tab, marked →; 6 lines end in spaces or tabs, highlighted."
		)
		// The argument list doesn't repeat it inline.
		expect(find(wrapper, "arg-command").text()).toBe("shown below")
		expect(find(wrapper, "shell").text()).toBe("PowerShell")
		expect(find(wrapper, "shell-artifact").text()).toBe("Windows.System.PowerShell")
		expect(find(wrapper, "hostname").text()).toBe("WIN-DC01")
		expect(find(wrapper, "agent").text()).toBe("· agent 001")
		expect(find(wrapper, "client").text()).toBe("· C.1234567890abcdef")
		expect(find(wrapper, "os").text()).toBe("· windows")
		expect(find(wrapper, "hidden-chars").exists()).toBe(false)
	})

	it("a command's invisible and control characters are escaped, with the warning", async () => {
		const wrapper = await mounted(commandAction(`Get-Process\r\nGet-${RLO}Service`))
		const pre = find(wrapper, "command-text")
		expect(pre.element.textContent).toBe("Get-Process⟨U+000D⟩\nGet-⟨U+202E⟩Service")
		expect(pre.element.textContent).not.toMatch(/[\r\u202E]/)
		expect(find(wrapper, "hidden-chars").text()).toBe(HIDDEN_CHARS_WARNING)
	})

	it("a collection shows its artifact and its parameters as a table of literal text", async () => {
		const wrapper = await mounted(
			collectAction({
				args: {
					hostname: "WIN-DC01",
					velociraptor_id: "C.1234567890abcdef",
					artifact_name: "Windows.System.Pslist",
					parameters: {
						env: [
							{ key: "ProcessRegex", value: "<b>x</b> **y** [z](https://evil.invalid)" },
							{ key: "CalculateHashes", value: "N" }
						]
					}
				}
			})
		)
		expect(find(wrapper, "title").text()).toBe("Collect a Velociraptor artifact")
		expect(find(wrapper, "artifact").text()).toBe("Windows.System.Pslist")
		expect(find(wrapper, "hostname").text()).toBe("WIN-DC01")
		const table = find(wrapper, "parameters")
		expect(table.element.tagName).toBe("TABLE")
		expect(table.findAll("th").map(th => th.text())).toEqual(["Parameter", "Value"])
		const rows = table.findAll('[data-testid="talon-approval-parameter"]')
		expect(rows.map(row => row.get('[data-testid="talon-approval-parameter-key"]').text())).toEqual([
			"ProcessRegex",
			"CalculateHashes"
		])
		const values = rows.map(row => row.get('[data-testid="talon-approval-parameter-value"]'))
		expect(values.map(value => value.text())).toEqual(["<b>x</b> **y** [z](https://evil.invalid)", "N"])
		for (const tag of ["b", "strong", "a"]) expect(table.find(tag).exists(), tag).toBe(false)
		expect(values[0].find("bdi").exists()).toBe(true)
		expect(find(wrapper, "arg-parameters").text()).toBe("shown below")
		expect(find(wrapper, "command").exists()).toBe(false)
	})

	it("a collection with no parameters says so; parameters in another shape are shown raw, with a note", async () => {
		const none = await mounted(
			collectAction({
				args: { hostname: "WIN-DC01", artifact_name: "Windows.System.Pslist", parameters: { env: [] } }
			})
		)
		expect(find(none, "parameters-none").text()).toBe("None: the artifact runs with its own defaults.")
		expect(find(none, "parameters").exists()).toBe(false)
		none.unmount()

		resetTalonActions()
		const odd = await mounted(
			collectAction({
				args: {
					hostname: "WIN-DC01",
					artifact_name: "Windows.System.Pslist",
					parameters: { ProcessRegex: "x" }
				}
			})
		)
		expect(find(odd, "parameters").exists()).toBe(false)
		expect(find(odd, "parameters-raw-note").exists()).toBe(true)
		expect(find(odd, "parameters-raw").text()).toBe('{\n  "ProcessRegex": "x"\n}')
	})

	it("a command's risk labels, its free-form shape and the endpoint-output banners render", async () => {
		const wrapper = await mounted(
			commandAction("Invoke-WebRequest https://x.invalid/a -OutFile C:\\t\\a\nRemove-Item C:\\t\\a", {
				provenance: {
					untrusted_seen: true,
					injection_detected: false,
					web_used: false,
					endpoint_output_used: true,
					copied_from_output: true,
					risk_labels: ["network_fetch", "delete_or_kill", "persistence", "made_up"],
					shape: "free-form"
				}
			})
		)
		const risks = wrapper.findAll('[data-testid="talon-approval-risk"]')
		expect(risks.map(r => r.text())).toEqual(["Network fetch", "Deletes or kills", "Persistence", "made_up"])
		expect(risks.map(r => r.attributes("data-risk"))).toEqual([
			"network_fetch",
			"delete_or_kill",
			"persistence",
			"made_up"
		])
		expect(find(wrapper, "risks-none").exists()).toBe(false)
		expect(find(wrapper, "risks-note").text()).toBe(RISK_LABELS_NOTE)

		expect(find(wrapper, "shape").text()).toBe("free-form")
		expect(find(wrapper, "shape").attributes("data-shape")).toBe("free-form")
		expect(find(wrapper, "shape-note").classes()).toContain("text-warning")
		expect(find(wrapper, "shape-note").text()).toContain("Free-form")

		const banners = wrapper.findAll('[data-testid="talon-approval-provenance"]')
		expect(banners.map(b => b.attributes("data-flag"))).toEqual([
			"untrusted_seen",
			"copied_from_output",
			"endpoint_output_used"
		])
		expect(banners.map(b => b.text())).toEqual([
			PROVENANCE_UNTRUSTED,
			PROVENANCE_COPIED,
			PROVENANCE_ENDPOINT_OUTPUT
		])
	})

	it("a read-only command with no labels says so; a missing shape is never read-only", async () => {
		const plain = await mounted(commandAction("Get-Process | Select-Object -First 50"))
		expect(find(plain, "shape").text()).toBe("read-only")
		expect(find(plain, "shape-note").classes()).not.toContain("text-warning")
		expect(find(plain, "risks-none").text()).toBe("none matched")
		expect(plain.findAll('[data-testid="talon-approval-risk"]')).toHaveLength(0)
		expect(plain.findAll('[data-testid="talon-approval-provenance"]')).toHaveLength(0)
		expect(find(plain, "whitespace").exists()).toBe(false)
		plain.unmount()

		resetTalonActions()
		const unlabelled = await mounted(
			commandAction("Get-Process", { provenance: { risk_labels: "network_fetch", shape: "READ-ONLY" } })
		)
		expect(find(unlabelled, "shape").text()).toBe("shape not labelled")
		expect(find(unlabelled, "shape").attributes("data-shape")).toBe("unknown")
		expect(find(unlabelled, "shape-note").classes()).toContain("text-warning")
		expect(find(unlabelled, "risks-none").exists()).toBe(true)
	})

	it("a collection carries the provenance banners too", async () => {
		const wrapper = await mounted(
			collectAction({
				provenance: { untrusted_seen: true, endpoint_output_used: true, injection_detected: true }
			})
		)
		expect(
			wrapper.findAll('[data-testid="talon-approval-provenance"]').map(b => b.attributes("data-flag"))
		).toEqual(["injection_detected", "untrusted_seen", "endpoint_output_used"])
		expect(find(wrapper, "provenance").text()).toBe(PROVENANCE_INJECTION)
	})

	it("approving a command confirms first, naming the host, the customer and the command's first line", async () => {
		const wrapper = await mounted(commandAction(HOSTILE_COMMAND))
		const summary = "Approve: run a PowerShell command on WIN-DC01 (agent 001) for customer ACME"
		expect(find(wrapper, "summary").text()).toBe(summary)
		expect(find(wrapper, "approve").attributes("aria-label")).toBe(summary)

		await find(wrapper, "approve").trigger("click")
		expect(approve).not.toHaveBeenCalled()
		const text = find(wrapper, "confirm-text")
		expect(text.text()).toContain("Run a command on the endpoint")
		expect(text.text()).toContain(summary)
		expect(find(wrapper, "confirm-first-line-label").text()).toBe(
			`Its first line (40 lines, ${HOSTILE_COMMAND.length.toLocaleString("en-US")} characters in all):`
		)
		const first = find(wrapper, "confirm-first-line")
		expect(first.element.tagName).toBe("PRE")
		expect(first.element.textContent).toBe("<script>alert(1)</script>")
		expect(first.find("script").exists()).toBe(false)
		expect(find(wrapper, "confirm-more").text()).toBe(
			"and 39 more lines: read the whole command on the card before running it."
		)
		expect(text.text()).toContain("SYSTEM on Windows")
		expect(find(wrapper, "confirm-run").text()).toBe("Run the command")

		approve.mockResolvedValueOnce(
			response(
				commandAction(HOSTILE_COMMAND, {
					state: "executed",
					talon_status: "executed",
					can_decide: false,
					execution_result: { success: true, message: "Command started", flow_id: "F.ABC123" }
				})
			)
		)
		await find(wrapper, "confirm-run").trigger("click")
		await flushPromises()
		expect(approve).toHaveBeenCalledTimes(1)
		expect(approve).toHaveBeenCalledWith(APPROVAL_ID)
		expect(find(wrapper, "status").text()).toBe("Executed")
		expect(find(wrapper, "flow").text()).toBe("Velociraptor flow F.ABC123")
	})

	it("the confirm's first line keeps its trailing spaces visible; a one-line command has no more lines", async () => {
		const two = await mounted(commandAction("Get-Process   \nGet-Service"))
		await find(two, "approve").trigger("click")
		const first = find(two, "confirm-first-line")
		expect(first.element.textContent).toBe("Get-Process   ")
		expect(first.findAll('[data-testid="talon-command-trailing"]').map(el => el.element.textContent)).toEqual([
			"   "
		])
		expect(find(two, "confirm-more").text()).toBe(
			"and 1 more line: read the whole command on the card before running it."
		)
		two.unmount()

		resetTalonActions()
		const one = await mounted(commandAction("Get-Process"))
		await find(one, "approve").trigger("click")
		expect(find(one, "confirm-first-line").element.textContent).toBe("Get-Process")
		expect(find(one, "confirm-first-line-label").text()).toBe("Its first line (1 line, 11 characters in all):")
		expect(find(one, "confirm-more").exists()).toBe(false)
	})

	it("approving a collection confirms first, naming the artifact, the host and the customer", async () => {
		const wrapper = await mounted(collectAction())
		const summary = "Approve: collect Windows.System.Pslist on WIN-DC01 (agent 001) for customer ACME"
		expect(find(wrapper, "summary").text()).toBe(summary)
		await find(wrapper, "approve").trigger("click")
		expect(find(wrapper, "confirm-text").text()).toContain("Collect a Velociraptor artifact")
		expect(find(wrapper, "confirm-text").text()).toContain(summary)
		expect(find(wrapper, "confirm-command").exists()).toBe(false)
		expect(find(wrapper, "confirm-run").text()).toBe("Collect")
		expect(approve).not.toHaveBeenCalled()
	})

	it("a command of a shell CoPilot doesn't name is shown by its artifact", async () => {
		const wrapper = await mounted(
			commandAction("dir", {
				args: {
					hostname: "WIN-DC01",
					velociraptor_id: "C.1234567890abcdef",
					artifact_name: "Odd.Artifact",
					command: "dir"
				}
			})
		)
		expect(find(wrapper, "shell").text()).toBe("not a known shell")
		expect(find(wrapper, "summary").text()).toBe(
			"Approve: run a command (Odd.Artifact) on WIN-DC01 (agent 001) for customer ACME"
		)
	})
})
