/**
 * How much code the highlighter (`directives/v-shiki.ts`) and the code viewer
 * (`components/common/CodeSource.vue`) take on, so a large or one-line sample can't hold the page up
 * (#1360).
 *
 * Language detection (flourite) and Shiki's TextMate tokenizer both slow down with the square of a
 * line's length, on the main thread. Measured on a 70,000-character one-line PowerShell script, the
 * common shape of an obfuscated dropper: detection took 87 s and tokenizing 26 s. Under these
 * limits the same script takes a few milliseconds, and a 100,000-character file of lines just under
 * the line limit about 100 ms.
 */

/** Longer lines are shown as they are, untokenized, inside an otherwise highlighted block (Shiki's `tokenizeMaxLineLength`). */
export const MAX_HIGHLIGHT_LINE = 1000

/** Larger code isn't highlighted at all: it is shown as plain text. */
export const MAX_HIGHLIGHT_CHARS = 100_000

/** How much of the code language detection reads, when no language is given. */
export const DETECT_SAMPLE_CHARS = 1000

/** How much a code viewer shows before "Show all"; copying always takes everything. */
export const MAX_SHOWN_CHARS = 200_000

/** The start of `code`, which is what language detection reads. */
export function detectionSample(code: string): string {
	return code.length > DETECT_SAMPLE_CHARS ? code.slice(0, DETECT_SAMPLE_CHARS) : code
}

/** Whether `code` is small enough to highlight. */
export function highlightable(code: string): boolean {
	return code.length <= MAX_HIGHLIGHT_CHARS
}

/** The part of `code` a viewer shows, and how many characters that leaves out (none when `all`). */
export function shownCode(code: string, all = false): { text: string; hidden: number } {
	if (all || code.length <= MAX_SHOWN_CHARS) return { text: code, hidden: 0 }
	// Never end on half of a surrogate pair (an emoji, a CJK extension character).
	const last = code.charCodeAt(MAX_SHOWN_CHARS - 1)
	const end = last >= 0xD800 && last <= 0xDBFF ? MAX_SHOWN_CHARS - 1 : MAX_SHOWN_CHARS
	return { text: code.slice(0, end), hidden: code.length - end }
}
