/**
 * SSE framing shared by the Talon chat streams (v1 `talon.ts`, v2 `talonV2.ts`).
 *
 * Bytes in, complete events out: events are separated by a blank line, CRLF line endings are
 * normalised after joining (so a pair split across reads still matches), a multi-byte character
 * split across reads is decoded whole, and `end()` hands back a final event the server closed
 * without a trailing blank line. What an event *means* is the caller's business.
 */
export interface SseFramer {
	/** The events completed by this read, in order. */
	push: (value: Uint8Array) => string[]
	/** Whatever is left once the stream has ended: at most one event. */
	end: () => string[]
}

export function createSseFramer(): SseFramer {
	const decoder = new TextDecoder()
	let buffer = ""

	return {
		push(value) {
			buffer = (buffer + decoder.decode(value, { stream: true })).replace(/\r\n/g, "\n")
			const events = buffer.split("\n\n")
			// The last element is incomplete: keep it for the next read.
			buffer = events.pop() || ""
			return events
		},
		end() {
			buffer = (buffer + decoder.decode()).replace(/\r\n/g, "\n")
			const rest = buffer
			buffer = ""
			return rest ? [rest] : []
		}
	}
}

/** The payloads of an event's `data:` lines. Comment lines (`: keepalive`) and other fields are skipped. */
export function sseDataLines(event: string): string[] {
	const out: string[] = []
	for (const line of event.split("\n")) {
		if (line.startsWith("data:")) out.push(line.slice(5))
	}
	return out
}
