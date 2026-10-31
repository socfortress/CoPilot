import type { TalonChatStreamResult } from "../talonChat"
import type { TalonChatChunk } from "@/types/talonChat"
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { useAuthStore } from "@/stores/auth"
import talonChat from "../talonChat"

const routerReplace = vi.hoisted(() => vi.fn())
vi.mock("@/router", () => ({
	default: {
		currentRoute: { value: { matched: [{}], name: "TalonChat", fullPath: "/talon?thread=th-1" } },
		replace: routerReplace
	}
}))

function body(text: string) {
	const bytes = new TextEncoder().encode(text)
	return new ReadableStream<Uint8Array>({
		start(controller) {
			controller.enqueue(bytes.slice(0, 10))
			controller.enqueue(bytes.slice(10))
			controller.close()
		}
	})
}

async function stream(response: Response | Error) {
	const fetchMock = vi.fn(() => (response instanceof Error ? Promise.reject(response) : Promise.resolve(response)))
	vi.stubGlobal("fetch", fetchMock)
	const chunks: TalonChatChunk[] = []
	const ends: TalonChatStreamResult[] = []
	await talonChat.streamChat("thread/1", "Hello", { onChunk: c => chunks.push(c), onEnd: r => ends.push(r) })
	return { fetchMock, chunks, ends }
}

beforeEach(() => setActivePinia(createPinia()))
afterEach(() => vi.unstubAllGlobals())

describe("streaming an Ask Talon turn", () => {
	it("posts only the message to CoPilot's portal route, and reads the stream", async () => {
		const { fetchMock, chunks, ends } = await stream(
			new Response(
				body(
					'data: {"type":"start"}\n\ndata: {"type":"text-start","id":"t"}\n\ndata: {"type":"text-delta","id":"t","delta":"Hi"}\n\ndata: {"type":"finish"}\n\ndata: [DONE]\n\n'
				),
				{ status: 200, headers: { "content-type": "text/event-stream" } }
			)
		)
		const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
		expect(url).toBe("/api/customer_portal/talon_chat/chat/thread%2F1")
		expect(init.method).toBe("POST")
		expect(JSON.parse(String(init.body))).toEqual({ message: "Hello" })
		expect(chunks.map(c => c.type)).toEqual(["start", "text-start", "text-delta", "finish"])
		expect(ends).toEqual([{ kind: "finished" }])
	})

	it("reports a refusal before the stream by its code, never its text", async () => {
		const { ends } = await stream(
			new Response(JSON.stringify({ detail: "portal chat is turned off for this customer", code: "portal_off" }), {
				status: 403,
				headers: { "content-type": "application/json" }
			})
		)
		expect(ends).toEqual([{ kind: "refused", status: 403, code: "portal_off" }])
	})

	it("reports a refusal without a code, and no answer at all", async () => {
		expect((await stream(new Response("Bad gateway", { status: 502 }))).ends).toEqual([
			{ kind: "refused", status: 502, code: null }
		])
		expect((await stream(new TypeError("offline"))).ends).toEqual([{ kind: "refused", status: null, code: null }])
	})

	it("reports a stream that stopped before finish as closed", async () => {
		const { ends } = await stream(new Response(body('data: {"type":"start"}\n\n'), { status: 200 }))
		expect(ends).toEqual([{ kind: "closed" }])
	})

	it("holds the user on the password change, as the HTTP client does, and shows no error", async () => {
		routerReplace.mockReset()
		useAuthStore().user = { access_token: "token", role: null, username: "jane", customer_codes: ["ACME"] }
		const { ends } = await stream(
			new Response(JSON.stringify({ detail: "change your password" }), {
				status: 403,
				headers: { "content-type": "application/json", "x-password-change-required": "true" }
			})
		)
		await new Promise(resolve => setTimeout(resolve, 0))
		expect(ends).toEqual([{ kind: "aborted" }])
		expect(useAuthStore().mustChangePassword).toBe(true)
		expect(routerReplace).toHaveBeenCalledWith({ name: "ChangePassword", query: { redirect: "/talon?thread=th-1" } })
	})
})
