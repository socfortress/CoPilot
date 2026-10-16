import type { BrowserContext, Route } from "@playwright/test"
import { readFileSync } from "node:fs"
import { expect, test } from "@playwright/test"
import { installMockBackend, signIn } from "./mock-backend"

/**
 * The Talon v2 chat (talon-analyst M5-5), behind the "Talon v2" setting: the AI Analyst page's chat
 * tab lists the analyst's threads with their customer, reads a thread's history back (a tool row,
 * an approval placeholder), streams a new turn (the golden `v2_tool` stream), starts a general
 * thread from the picker, says "waiting for a decision" on a 409, and locks a thread whose
 * customer was taken away. What is asserted is what the page shows and what it sends.
 */

const ACME_THREAD = "0b6f0c55-7a39-4e57-9d6e-3f1a2b3c4d5e"
const LOCKED_THREAD = "1c7a1d66-8b4a-4f68-8e7f-4a2b3c4d5e6f"
const NEW_THREAD = "2d8b2e77-9c5b-4a79-9f80-5b3c4d5e6f70"
const APPROVAL = "3f1c9a2e-5b7d-4e8f-9a01-2c3d4e5f6a7b"

function thread(id: string, extra: Record<string, unknown> = {}) {
	return {
		id,
		title: null,
		customer_code: null,
		status: "active",
		created_at: "2026-10-16T08:00:00+00:00",
		updated_at: "2026-10-16T08:00:00+00:00",
		archived_at: null,
		accessible: true,
		context_tokens: null,
		...extra
	}
}

const HISTORY = [
	{
		id: "r1-user",
		role: "user",
		parts: [{ type: "text", text: "close alert 840?", state: "done" }],
		metadata: { created_at: "2026-10-16T08:00:00+00:00" }
	},
	{
		id: "r1-assistant",
		role: "assistant",
		parts: [
			{ type: "text", text: "I can close it.", state: "done" },
			{
				type: "tool-set_alert_status",
				toolCallId: "call_q",
				state: "approval-requested",
				input: { alert_id: 840, status: "CLOSED", reason: "a known scanner" },
				approval: { id: APPROVAL, status: "pending" }
			}
		],
		metadata: { created_at: "2026-10-16T08:00:01+00:00", status: "completed" }
	}
]

const TOOL_STREAM = readFileSync(new URL("../src/api/__tests__/fixtures/talon-v2/v2_tool.txt", import.meta.url), "utf8")

async function installTalonV2Mock(context: BrowserContext) {
	const sent: { path: string; body: unknown }[] = []
	const threads = [
		thread(ACME_THREAD, { title: "ACME triage", customer_code: "ACME", context_tokens: 1055 }),
		thread(LOCKED_THREAD, { title: "Old customer", customer_code: "GLOBEX", accessible: false })
	]
	let chats = 0
	const json = (route: Route, body: unknown, status = 200) =>
		route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) })

	// Registered after the generic mock, so these run first; anything else falls back to it.
	await context.route(
		url => url.pathname.startsWith("/api/talon/v2/"),
		async route => {
			const request = route.request()
			const path = new URL(request.url()).pathname.replace(/^\/api/, "")
			const method = request.method()

			if (path === "/talon/v2/availability") return json(route, { success: true, message: "on", enabled: true })
			if (path === "/talon/v2/threads" && method === "GET") return json(route, { threads, next: null })
			if (path === "/talon/v2/threads" && method === "POST") {
				const body = request.postDataJSON()
				sent.push({ path, body })
				const created = thread(NEW_THREAD, { title: body.title, customer_code: body.customer_code })
				threads.unshift(created)
				return json(route, created, 201)
			}
			if (path === `/talon/v2/threads/${ACME_THREAD}/messages`) {
				return json(route, { thread: threads.find(t => t.id === ACME_THREAD), messages: HISTORY, next: null })
			}
			if (path === `/talon/v2/threads/${NEW_THREAD}/messages`) {
				return json(route, { thread: threads[0], messages: [], next: null })
			}
			if (path.startsWith("/talon/v2/chat/")) {
				sent.push({ path, body: request.postDataJSON() })
				chats += 1
				if (chats === 1) {
					return route.fulfill({
						status: 200,
						headers: { "content-type": "text/event-stream", "x-vercel-ai-ui-message-stream": "v1" },
						body: TOOL_STREAM
					})
				}
				return json(route, { detail: "an action in this thread is waiting for a decision in CoPilot" }, 409)
			}
			return json(route, { detail: "Not Found" }, 404)
		}
	)
	return sent
}

test.describe("Talon v2 chat", () => {
	test("threads, history read back, a streamed turn, a new general thread, 409 and a locked thread", async ({
		context,
		page
	}) => {
		await installMockBackend(context)
		const sent = await installTalonV2Mock(context)
		await signIn(page)

		await page.goto("/ai-analyst")
		await page.locator(".n-tabs-tab", { hasText: /^\s*Talon Chat\s*$/ }).click()

		// The rail: each thread with its customer; the locked one marked.
		const rail = page.getByTestId("talon-v2-thread-list")
		await expect(rail.getByTestId("talon-v2-thread")).toHaveCount(2)
		const acme = rail.locator(`[data-thread-id="${ACME_THREAD}"]`)
		await expect(acme.getByTestId("talon-v2-thread-customer")).toHaveText("ACME")
		await expect(
			rail.locator(`[data-thread-id="${LOCKED_THREAD}"]`).getByTestId("talon-v2-thread-locked")
		).toBeVisible()

		// The newest thread opens with its history: the text, the tool row and the approval placeholder.
		const conversation = page.getByTestId("talon-v2-conversation")
		await expect(conversation).toHaveAttribute("data-thread-id", ACME_THREAD)
		await expect(conversation.getByTestId("talon-v2-user-text")).toHaveText("close alert 840?")
		await expect(conversation.getByTestId("talon-v2-tool-name")).toHaveText("set_alert_status")
		await expect(conversation.getByTestId("talon-v2-approval")).toHaveAttribute("data-approval-id", APPROVAL)
		await expect(conversation.getByTestId("talon-v2-approval")).toHaveText("Approval pending")
		await expect(conversation.getByTestId("talon-v2-context")).toHaveText("context 1k")

		// A new turn streams in: the golden v2_tool stream.
		await conversation.getByTestId("talon-v2-input").locator("textarea").fill("check ws-1")
		await conversation.getByTestId("talon-v2-send").click()
		const reply = conversation.getByTestId("talon-v2-message").last()
		await expect(reply).toHaveAttribute("data-status", "completed")
		await expect(reply.getByTestId("talon-v2-text").last()).toContainText("Done.")
		await expect(reply.locator('[data-tool-call-id="call_1"]')).toHaveAttribute("data-state", "output-available")
		await expect(reply.getByTestId("talon-v2-usage")).toContainText("2 requests")
		expect(sent.at(-1)?.path).toBe(`/talon/v2/chat/${ACME_THREAD}`)
		expect(sent.at(-1)?.body).toMatchObject({ message: "check ws-1" })

		// A general thread from the picker: "General (no customer data)" is the default.
		await page.getByTestId("talon-v2-new-thread-button").click()
		const picker = page.getByTestId("talon-v2-new-thread")
		await expect(picker.getByTestId("talon-v2-new-thread-customer")).toContainText("General (no customer data)")
		await picker.getByTestId("talon-v2-new-thread-title").locator("input").fill("Sysmon questions")
		await picker.getByTestId("talon-v2-new-thread-create").click()
		expect(sent.find(s => s.path === "/talon/v2/threads")?.body).toEqual({
			title: "Sysmon questions",
			customer_code: null
		})
		await expect(conversation).toHaveAttribute("data-thread-id", NEW_THREAD)
		await expect(
			rail.locator(`[data-thread-id="${NEW_THREAD}"]`).getByTestId("talon-v2-thread-customer")
		).toHaveText("General")

		// A 409: waiting for a decision, and the message goes back to the composer.
		await conversation.getByTestId("talon-v2-input").locator("textarea").fill("and now?")
		await conversation.getByTestId("talon-v2-send").click()
		await expect(conversation.getByTestId("talon-v2-notice")).toContainText("Waiting for a decision")
		await expect(conversation.getByTestId("talon-v2-input").locator("textarea")).toHaveValue("and now?")

		// A thread whose customer was taken away: not read, and the composer is disabled.
		await rail.locator(`[data-thread-id="${LOCKED_THREAD}"]`).click()
		await expect(conversation).toHaveAttribute("data-thread-id", LOCKED_THREAD)
		await expect(conversation.getByTestId("talon-v2-notice")).toContainText(
			"Access to this thread's customer was removed"
		)
		await expect(conversation.getByTestId("talon-v2-input").locator("textarea")).toBeDisabled()
	})

	test("with the setting off the page shows the v1 chat", async ({ context, page }) => {
		await installMockBackend(context)
		await context.route(
			url => url.pathname === "/api/talon/v2/availability",
			route =>
				route.fulfill({
					status: 200,
					contentType: "application/json",
					body: JSON.stringify({ success: true, message: "off", enabled: false })
				})
		)
		await signIn(page)
		await page.goto("/ai-analyst")
		await page.locator(".n-tabs-tab", { hasText: /^\s*Talon Chat\s*$/ }).click()
		await expect(page.getByPlaceholder("Ask Talon...")).toBeVisible()
		await expect(page.getByRole("button", { name: /New session/ })).toBeVisible()
		await expect(page.getByTestId("talon-v2-chat")).toHaveCount(0)
	})
})
