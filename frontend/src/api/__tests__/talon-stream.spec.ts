/**
 * Talon chat SSE parsing (`Api.talon.streamMessage`).
 *
 * Talon streams `data: {"type":"text"}` events then `data: {"type":"done"}`. On a
 * failure it sends `data: {"error":"Talon request failed: …"}` instead of `done`,
 * possibly after part of the reply has streamed, and it sends `: keepalive`
 * comments while a reply is being worked on. These tests pin that each reply ends
 * in exactly one of `onDone` / `onError`, with the error's own text, and that a
 * stream that just stops is an error, not a finished reply.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/stores/auth", () => ({
	useAuthStore: () => ({ userToken: "token" })
}))

const { default: talon, TALON_STREAM_CLOSED } = await import("../endpoints/talon")

/** A streamed response whose body arrives as `chunks`, then closes (or fails with `failWith`). */
function sseResponse(chunks: string[], failWith?: Error) {
	const encoder = new TextEncoder()
	const pending = [...chunks]
	// One chunk per read, like a network stream: erroring a stream drops anything still queued.
	const body = new ReadableStream<Uint8Array>({
		pull(controller) {
			const chunk = pending.shift()
			if (chunk !== undefined) controller.enqueue(encoder.encode(chunk))
			else if (failWith) controller.error(failWith)
			else controller.close()
		}
	})
	return new Response(body, { status: 200, headers: { "Content-Type": "text/event-stream" } })
}

async function stream(response: Response) {
	vi.mocked(fetch).mockResolvedValueOnce(response)
	const chunks: string[] = []
	const onDone = vi.fn()
	const onError = vi.fn()
	await talon.streamMessage("hi", chunk => chunks.push(chunk), onDone, onError)
	return { text: chunks.join(""), onDone, onError }
}

describe("talon streamMessage", () => {
	beforeEach(() => {
		vi.stubGlobal("fetch", vi.fn())
	})

	afterEach(() => {
		vi.unstubAllGlobals()
	})

	it("streams text, skips keepalive comments and finishes on done", async () => {
		const { text, onDone, onError } = await stream(
			sseResponse([
				": keepalive\n\n",
				'data: {"type":"text","content":"Hello"}\n\n',
				'data: {"type":"text","content":" analyst"}\n\n',
				'data: {"type":"done"}\n\n'
			])
		)

		expect(text).toBe("Hello analyst")
		expect(onDone).toHaveBeenCalledOnce()
		expect(onError).not.toHaveBeenCalled()
	})

	it("reports an error event's text, after the text that streamed before it", async () => {
		const { text, onDone, onError } = await stream(
			sseResponse([
				'data: {"type":"text","content":"Partial"}\n\n',
				'data: {"error":"Talon request failed: turn limit reached: 30 tool calls"}\n\n'
			])
		)

		expect(text).toBe("Partial")
		expect(onError).toHaveBeenCalledExactlyOnceWith("Talon request failed: turn limit reached: 30 tool calls")
		expect(onDone).not.toHaveBeenCalled()
	})

	it("reports an error event that arrives before any text", async () => {
		const { text, onDone, onError } = await stream(
			sseResponse(['data: {"error":"Talon request failed: a reply is still streaming"}\n\n'])
		)

		expect(text).toBe("")
		expect(onError).toHaveBeenCalledExactlyOnceWith("Talon request failed: a reply is still streaming")
		expect(onDone).not.toHaveBeenCalled()
	})

	it("joins events split across reads", async () => {
		const { text, onDone } = await stream(
			sseResponse(['data: {"type":"text","con', 'tent":"split"}\n', '\ndata: {"type":"done"}\n\n'])
		)

		expect(text).toBe("split")
		expect(onDone).toHaveBeenCalledOnce()
	})

	it("accepts CRLF line endings", async () => {
		const { text, onDone } = await stream(
			sseResponse(['data: {"type":"text","content":"crlf"}\r', '\n\r\ndata: {"type":"done"}\r\n\r\n'])
		)

		expect(text).toBe("crlf")
		expect(onDone).toHaveBeenCalledOnce()
	})

	it("handles a final event without a trailing blank line", async () => {
		const { onDone, onError } = await stream(sseResponse(['data: {"error":"Talon request failed: cut off"}']))

		expect(onError).toHaveBeenCalledExactlyOnceWith("Talon request failed: cut off")
		expect(onDone).not.toHaveBeenCalled()
	})

	it("treats a stream that closes without done as cut off, not finished", async () => {
		const { text, onDone, onError } = await stream(sseResponse(['data: {"type":"text","content":"Half a"}\n\n']))

		expect(text).toBe("Half a")
		expect(onError).toHaveBeenCalledExactlyOnceWith(TALON_STREAM_CLOSED)
		expect(onDone).not.toHaveBeenCalled()
	})

	it("treats a connection that fails mid-stream as cut off", async () => {
		const { text, onDone, onError } = await stream(
			sseResponse(['data: {"type":"text","content":"Half a"}\n\n'], new TypeError("network error"))
		)

		expect(text).toBe("Half a")
		expect(onError).toHaveBeenCalledExactlyOnceWith(TALON_STREAM_CLOSED)
		expect(onDone).not.toHaveBeenCalled()
	})

	it("reports a non-2xx response", async () => {
		const { onDone, onError } = await stream(new Response("nope", { status: 502 }))

		expect(onError).toHaveBeenCalledExactlyOnceWith("Request failed with status 502")
		expect(onDone).not.toHaveBeenCalled()
	})

	it("stays silent when the caller aborts", async () => {
		vi.mocked(fetch).mockRejectedValueOnce(new DOMException("aborted", "AbortError"))
		const onDone = vi.fn()
		const onError = vi.fn()

		await talon.streamMessage("hi", vi.fn(), onDone, onError)

		expect(onDone).not.toHaveBeenCalled()
		expect(onError).not.toHaveBeenCalled()
	})
})
