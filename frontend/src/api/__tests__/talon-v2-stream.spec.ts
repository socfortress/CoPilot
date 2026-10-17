/**
 * `Api.talonV2.streamChat`: one chat request through CoPilot's v2 proxy.
 *
 * Exactly one ending is reported: `finished` (a `finish` or `[DONE]`), `closed` (the stream just
 * stopped), `aborted` (the caller's signal) or `refused` (a status before the stream, with the
 * refusal's own short text or the fixed one). The browser sends only `{message, message_id}`;
 * CoPilot builds the AI SDK request itself.
 */
import type { TalonV2StreamResult } from "../endpoints/talonV2"
import type { TalonV2Chunk } from "@/types/talonV2"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/stores/auth", () => ({ useAuthStore: () => ({ userToken: "token" }) }))
vi.mock("../http-client", () => ({ HttpClient: {} }))

const { default: talonV2, refusalDetail } = await import("../endpoints/talonV2")
const { TALON_V2_FAILED, TALON_V2_STREAM_CLOSED } = await import("../talonV2Parser")

const encoder = new TextEncoder()
const THREAD = "0b6f0c55-7a39-4e57-9d6e-3f1a2b3c4d5e"

function streamResponse(chunks: string[], options: { hang?: boolean; failWith?: Error } = {}) {
	const pending = [...chunks]
	const body = new ReadableStream<Uint8Array>({
		pull(controller) {
			const chunk = pending.shift()
			if (chunk !== undefined) {
				controller.enqueue(encoder.encode(chunk))
				return
			}
			if (options.hang) return new Promise<void>(() => {})
			if (options.failWith) {
				controller.error(options.failWith)
				return
			}
			controller.close()
		}
	})
	return new Response(body, { status: 200, headers: { "Content-Type": "text/event-stream" } })
}

async function run(response: Response | Promise<Response>, signal?: AbortSignal) {
	vi.mocked(fetch).mockImplementationOnce(() => Promise.resolve(response))
	const chunks: TalonV2Chunk[] = []
	const ends: TalonV2StreamResult[] = []
	await talonV2.streamChat(
		THREAD,
		{ message: "hello", message_id: "copilot-1" },
		{ onChunk: c => chunks.push(c), onEnd: r => ends.push(r) },
		signal
	)
	return { chunks, ends }
}

const TEXT = [
	'data: {"type":"start"}\n\n',
	'data: {"type":"text-delta","id":"text-1","delta":"hi"}\n\n',
	'data: {"type":"finish"}\n\n',
	"data: [DONE]\n\n"
]

describe("talon v2 chat stream", () => {
	beforeEach(() => {
		vi.stubGlobal("fetch", vi.fn())
	})
	afterEach(() => {
		vi.unstubAllGlobals()
	})

	it("posts only the message to CoPilot's proxy, with the user's token", async () => {
		await run(streamResponse(TEXT))
		const [url, init] = vi.mocked(fetch).mock.calls[0]
		expect(url).toBe(`/api/talon/v2/chat/${THREAD}`)
		expect(init?.method).toBe("POST")
		expect(JSON.parse(String(init?.body))).toEqual({ message: "hello", message_id: "copilot-1" })
		expect(init?.headers).toMatchObject({ Authorization: "Bearer token", "Content-Type": "application/json" })
	})

	it("reports finished once, after the chunks", async () => {
		const { chunks, ends } = await run(streamResponse(TEXT))
		expect(chunks.map(c => c.type)).toEqual(["start", "text-delta", "finish"])
		expect(ends).toEqual([{ kind: "finished" }])
	})

	it("stops reading at [DONE] even if the server keeps the connection open", async () => {
		const { ends } = await run(streamResponse(TEXT, { hang: true }))
		expect(ends).toEqual([{ kind: "finished" }])
	})

	it("a finish without [DONE] is finished", async () => {
		const { ends } = await run(streamResponse(TEXT.slice(0, 3)))
		expect(ends).toEqual([{ kind: "finished" }])
	})

	it("a stream that stops, or fails, without finish is closed", async () => {
		expect((await run(streamResponse(TEXT.slice(0, 2)))).ends).toEqual([
			{ kind: "closed", errorText: TALON_V2_STREAM_CLOSED }
		])
		expect((await run(streamResponse(TEXT.slice(0, 2), { failWith: new TypeError("network") }))).ends).toEqual([
			{ kind: "closed", errorText: TALON_V2_STREAM_CLOSED }
		])
	})

	it("an abort mid-stream is aborted, with the chunks before it handed on", async () => {
		const controller = new AbortController()
		const pending = run(streamResponse(TEXT.slice(0, 2), { hang: true }), controller.signal)
		// The stream hangs after its two chunks; the reader is cancelled by the abort.
		await new Promise(resolve => setTimeout(resolve, 10))
		controller.abort()
		const { chunks, ends } = await pending
		expect(chunks.map(c => c.type)).toEqual(["start", "text-delta"])
		expect(ends).toEqual([{ kind: "aborted" }])
	})

	it.each([
		[409, { detail: "an action in this thread is waiting for a decision in CoPilot" }],
		[403, { detail: "access to this thread's customer was removed" }],
		[403, { detail: "your alert access changed since this thread began; start a new thread" }],
		[404, { detail: "thread not found" }],
		[422, { detail: [{ loc: ["body"], msg: "x" }] }],
		[500, "<html>Traceback</html>"]
	])("a %s before the stream is refused with its own short text or the fixed one", async (status, body) => {
		const response = new Response(typeof body === "string" ? body : JSON.stringify(body), {
			status,
			headers: { "Content-Type": typeof body === "string" ? "text/html" : "application/json" }
		})
		const { chunks, ends } = await run(response)
		expect(chunks).toEqual([])
		const detail = typeof body === "object" && typeof body.detail === "string" ? body.detail : TALON_V2_FAILED
		expect(ends).toEqual([{ kind: "refused", status, detail }])
	})

	it("no answer at all is refused with the fixed text", async () => {
		vi.mocked(fetch).mockRejectedValueOnce(new TypeError("Failed to fetch"))
		const ends: TalonV2StreamResult[] = []
		await talonV2.streamChat(THREAD, { message: "x" }, { onChunk: () => {}, onEnd: r => ends.push(r) })
		expect(ends).toEqual([{ kind: "refused", status: null, detail: TALON_V2_FAILED }])
	})

	it("refusalDetail takes a short string detail or CoPilot's message, else the fixed text", () => {
		expect(refusalDetail({ detail: "thread not found" })).toBe("thread not found")
		expect(refusalDetail({ success: false, message: "customer_code is not a customer" })).toBe(
			"customer_code is not a customer"
		)
		expect(refusalDetail({ detail: "x".repeat(301) })).toBe(TALON_V2_FAILED)
		expect(refusalDetail({ detail: [{ msg: "x" }] })).toBe(TALON_V2_FAILED)
		expect(refusalDetail("<html>")).toBe(TALON_V2_FAILED)
		expect(refusalDetail(null)).toBe(TALON_V2_FAILED)
	})
})
