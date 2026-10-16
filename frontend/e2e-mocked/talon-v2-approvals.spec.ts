import type { BrowserContext, Route } from "@playwright/test"
import { readFileSync } from "node:fs"
import { expect, test } from "@playwright/test"
import { installMockBackend, signIn } from "./mock-backend"

/**
 * Talon v2 chat action proposals (talon-analyst M5-11, CoPilot M5-11b), behind the "Talon v2"
 * setting: a streamed turn proposes closing an alert (the golden `v2_approval` stream), its card
 * reads CoPilot's record of the proposal (`GET /api/talon/actions/{id}`, never the stream's
 * arguments), the composer waits for the decision, the analyst approves, the card says executed,
 * and the thread resumes exactly once with an empty message, whose stream answers the call. The
 * Approvals tab lists the proposal with a count badge while it waits. What is asserted is what the
 * page shows and what it sends.
 */

const THREAD = "0b6f0c55-7a39-4e57-9d6e-3f1a2b3c4d5e"
// The golden stream's approval card id.
const APPROVAL = "3f1c9a2e-5b7d-4e8f-9a01-2c3d4e5f6a7b"

const APPROVAL_STREAM = readFileSync(
	new URL("../src/api/__tests__/fixtures/talon-v2/v2_approval.txt", import.meta.url),
	"utf8"
)

/** talon-analyst's resume (SPEC §9.5): the call answered by the record, then the model's text. */
const RESUME_STREAM = [
	{ type: "start" },
	{ type: "start-step" },
	{ type: "tool-output-available", toolCallId: "call_q", output: { status: "done", spilled: false } },
	{ type: "text-start", id: "text-2" },
	{ type: "text-delta", id: "text-2", delta: "Alert 840 is closed." },
	{ type: "text-end", id: "text-2" },
	{ type: "finish-step" },
	{ type: "finish" }
]
	.map(chunk => `data: ${JSON.stringify(chunk)}\n\n`)
	.concat("data: [DONE]\n\n")
	.join("")

function naiveUtc(hours: number) {
	return new Date(Date.now() + hours * 3600_000).toISOString().slice(0, 19)
}

function record(extra: Record<string, unknown> = {}) {
	return {
		id: APPROVAL,
		thread_id: THREAD,
		customer_code: "ACME",
		requester_user_id: "1",
		action: "set_alert_status",
		side_effect: "external-action",
		executes_through: "PUT /api/incidents/db_operations/alert/status",
		// CoPilot's record: what the card shows, whatever the stream's input said.
		target: { alert_id: 840 },
		args: { alert_id: 840, status: "CLOSED" },
		reason: "a known scanner <b>trust me</b>",
		links: false,
		provenance: { untrusted_seen: false, injection_detected: false, web_used: true },
		talon_status: "pending",
		state: "pending",
		state_reason: null,
		expired: false,
		expires_at: naiveUtc(4),
		created_at: naiveUtc(0),
		decision: null,
		approver_user_id: null,
		approver_username: null,
		decided_at: null,
		execution_result: null,
		executed_at: null,
		outcome_reported: false,
		can_decide: true,
		is_requester: true,
		...extra
	}
}

const EXECUTED = record({
	talon_status: "executed",
	state: "executed",
	decision: "approve",
	approver_user_id: 1,
	approver_username: "admin",
	decided_at: naiveUtc(0),
	execution_result: { success: true, message: "Alert status updated", status_code: 200 },
	executed_at: naiveUtc(0),
	outcome_reported: true,
	can_decide: false
})

async function installApprovalsMock(context: BrowserContext) {
	const chats: unknown[] = []
	const decisions: string[] = []
	let decided = false
	const json = (route: Route, body: unknown, status = 200) =>
		route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) })

	await context.route(
		url => url.pathname.startsWith("/api/talon/"),
		async route => {
			const request = route.request()
			const path = new URL(request.url()).pathname.replace(/^\/api/, "")
			const method = request.method()

			if (path === "/talon/v2/availability") return json(route, { success: true, message: "on", enabled: true })
			if (path === "/talon/v2/threads" && method === "GET") {
				return json(route, {
					threads: [
						{
							id: THREAD,
							title: "ACME triage",
							customer_code: "ACME",
							status: "active",
							created_at: "2026-10-16T08:00:00+00:00",
							updated_at: "2026-10-16T08:00:00+00:00",
							archived_at: null,
							accessible: true,
							context_tokens: null
						}
					],
					next: null
				})
			}
			if (path === `/talon/v2/threads/${THREAD}/messages`) {
				return json(route, { thread: { id: THREAD }, messages: [], next: null })
			}
			if (path === `/talon/v2/chat/${THREAD}`) {
				const body = request.postDataJSON()
				chats.push(body)
				if (body.message === "" && !decided) {
					return json(
						route,
						{ success: false, message: "an action in this thread is waiting for a decision in CoPilot" },
						409
					)
				}
				return route.fulfill({
					status: 200,
					headers: { "content-type": "text/event-stream", "x-vercel-ai-ui-message-stream": "v1" },
					body: body.message === "" ? RESUME_STREAM : APPROVAL_STREAM
				})
			}
			if (path === "/talon/actions" && method === "GET") {
				const pending = chats.length > 0 && !decided
				return json(route, { success: true, message: "", actions: pending ? [record()] : [] })
			}
			if (path === `/talon/actions/${APPROVAL}` && method === "GET") {
				return json(route, {
					success: true,
					message: "Action retrieved",
					action: decided ? EXECUTED : record()
				})
			}
			if (path === `/talon/actions/${APPROVAL}/approve` && method === "POST") {
				decisions.push("approve")
				decided = true
				return json(route, { success: true, message: "Action executed", action: EXECUTED })
			}
			return json(route, { detail: "Not Found" }, 404)
		}
	)
	return { chats, decisions }
}

test.describe("Talon v2 action proposals", () => {
	test("propose, approve, executed, resume", async ({ context, page }) => {
		await installMockBackend(context)
		const sent = await installApprovalsMock(context)
		await signIn(page)

		await page.goto("/ai-analyst")
		await page.locator(".n-tabs-tab", { hasText: /^\s*Talon Chat\s*$/ }).click()
		const conversation = page.getByTestId("talon-v2-conversation")
		await expect(conversation).toHaveAttribute("data-thread-id", THREAD)

		// The model proposes closing alert 840 (the golden v2_approval stream).
		const input = conversation.getByTestId("talon-v2-input").locator("textarea")
		await input.fill("close alert 840?")
		await conversation.getByTestId("talon-v2-send").click()

		// The card: CoPilot's record, apart from the tool row with the model's own arguments.
		const card = conversation.getByTestId("talon-approval-card")
		await expect(card).toHaveAttribute("data-approval-id", APPROVAL)
		await expect(card.getByTestId("talon-approval-status")).toHaveText("Waiting for a decision")
		await expect(card.getByTestId("talon-approval-title")).toHaveText("Set the alert's status")
		await expect(card.getByTestId("talon-approval-alert-link")).toHaveText("Alert #840")
		await expect(card.getByTestId("talon-approval-reason-text")).toHaveText("a known scanner <b>trust me</b>")
		await expect(card.locator("b")).toHaveCount(0)
		await expect(card.getByTestId("talon-approval-provenance")).toHaveAttribute("data-flag", "web_used")
		await expect(conversation.getByTestId("talon-v2-tool").getByTestId("talon-approval-card")).toHaveCount(0)

		// The thread waits: the composer says so and takes nothing.
		await expect(conversation.getByTestId("talon-v2-notice")).toContainText("Waiting for a decision")
		await expect(input).toBeDisabled()

		// The Approvals tab lists it, with its count.
		const approvalsTab = page.locator(".n-tabs-tab", { hasText: /Approvals/ })
		await approvalsTab.click()
		await page.getByTestId("talon-approvals-refresh").click()
		await expect(page.getByTestId("talon-approvals-badge")).toContainText("1")
		const row = page.getByTestId("talon-approvals-row")
		await expect(row).toHaveAttribute("data-approval-id", APPROVAL)
		await expect(row.getByTestId("talon-approvals-row-target")).toHaveText("alert #840")

		// Back in the thread, the analyst approves it; CoPilot runs it.
		await page.locator(".n-tabs-tab", { hasText: /^\s*Talon Chat\s*$/ }).click()
		await card.getByTestId("talon-approval-approve").click()
		await expect(card.getByTestId("talon-approval-status")).toHaveText("Executed")
		await expect(card.getByTestId("talon-approval-result")).toHaveText("Result: Alert status updated")
		await expect(card.getByRole("button")).toHaveCount(0)
		expect(sent.decisions).toEqual(["approve"])
		// Nothing waits any more: the Approvals badge goes.
		await expect(page.getByTestId("talon-approvals-badge")).toHaveCount(0)

		// Every proposal final: the thread resumes once, with an empty message, rendered as any turn.
		const reply = conversation.getByTestId("talon-v2-message").last()
		await expect(reply).toHaveAttribute("data-status", "completed")
		await expect(reply.getByTestId("talon-v2-text")).toContainText("Alert 840 is closed.")
		await expect(reply.locator('[data-tool-call-id="call_q"]')).toHaveAttribute("data-state", "output-available")
		await expect(input).toBeEnabled()
		await expect(conversation.getByTestId("talon-v2-notice")).toHaveCount(0)
		expect(sent.chats).toEqual([expect.objectContaining({ message: "close alert 840?" }), { message: "" }])

		// Nothing is sent again: no second resume while the page stays open.
		await page.waitForTimeout(1500)
		expect(sent.chats).toHaveLength(2)
	})
})
