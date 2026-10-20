import type { VNode } from "vue"
import type { CommandSegment } from "./approvals"
import { computed, defineComponent, h, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue"
import { commandSegments, MIN_WRAP_COLUMNS, WRAP_COLUMNS, wrapSegments } from "./approvals"

const TRAILING_MARK =
	"bg-[rgba(var(--warning-color-rgb)/0.35)] outline-1 outline-[rgba(var(--warning-color-rgb)/0.7)] outline-dashed"
/** The gutter's width in `ch` beyond the digits of the last line number. */
const GUTTER_PAD = 1.5

/**
 * A command exactly as it would run (talon-analyst's endpoint actions plan, EA-4): text nodes,
 * never HTML, Markdown or links, and every character visible.
 *
 * - **Our rows are the only wrap.** Each line is cut into rows (`approvals.ts:wrapSegments`) at
 *   `columns`, or fewer when the box is narrower (measured from the box and the font), and drawn
 *   with `white-space: pre`, so the browser never wraps again: a space where a row wraps would look
 *   like no space, so ours are drawn as `␠`. Every row after a line's first is marked `↪` in the
 *   gutter, which numbers the lines.
 * - Tabs keep the tab character and are marked by CSS; four or more spaces in a row are shown as
 *   `⟨␠×N⟩`; whitespace that ends a line is highlighted; non-ASCII runs are highlighted; a character
 *   nobody can see is shown as `⟨U+000D⟩` (`approvals.ts:commandSegments`).
 * - The box scrolls, and says so in text that doesn't depend on the OS drawing a scrollbar: "N
 *   lines, scroll to see all" when it holds more rows than it shows, and a sideways cue if a row is
 *   still wider than the box (a font with wider glyphs than measured).
 *
 * Gutter numbers and markers are CSS `content`, not text. Rendered in code, not a template, so a
 * template's own line breaks can't reach the `<pre>`. `inline` renders the rows without a gutter
 * or a height limit, for a parameter value.
 */
export default defineComponent({
	name: "TalonCommandText",
	props: {
		text: { type: String, default: "" },
		/** The most columns a row holds (fewer when the box is narrower). */
		columns: { type: Number, default: WRAP_COLUMNS },
		/** Rows the box shows before it scrolls. */
		maxRows: { type: Number, default: 16 },
		/** The number of the text's first line in the whole command (the confirm shows one line). */
		firstLineNumber: { type: Number, default: 1 },
		/** Lines in the whole command, for the scroll cue (the text's own by default). */
		totalLines: { type: Number, default: 0 },
		/** No gutter and no height limit: a parameter value. */
		inline: { type: Boolean, default: false },
		testId: { type: String, default: "talon-command-text" }
	},
	setup(props) {
		const lines = computed<CommandSegment[][]>(() => commandSegments(props.text))
		const lastNumber = computed(() => props.firstLineNumber + lines.value.length - 1)
		const gutterCh = computed(() => (props.inline ? 0 : String(lastNumber.value).length + GUTTER_PAD))
		const box = ref<HTMLElement | null>(null)
		const probe = ref<HTMLElement | null>(null)
		/** Columns that fit the box, measured; null until measured (or where nothing is laid out). */
		const fits = ref<number | null>(null)
		const columns = computed(() => {
			const most = Math.max(MIN_WRAP_COLUMNS, Math.floor(props.columns))
			return fits.value === null ? most : Math.max(MIN_WRAP_COLUMNS, Math.min(most, fits.value))
		})
		const rows = computed(() => lines.value.map(line => wrapSegments(line, columns.value)))
		const rowCount = computed(() => rows.value.reduce((sum, line) => sum + line.length, 0))
		const tallOverflow = ref(false)
		const wideOverflow = ref(false)
		const scrolls = computed(() => !props.inline && (rowCount.value > props.maxRows || tallOverflow.value))
		let observer: ResizeObserver | null = null

		function measure() {
			const el = box.value
			if (!el) return
			// Layout widths (`offsetWidth`, `clientWidth`), never `getBoundingClientRect`: a transform (NModal's
			// scale-in) shrinks the latter while it animates, which would cut the rows too short.
			const charWidth = (probe.value?.offsetWidth ?? 0) / 10
			// Not inline: a table cell's width follows its content, so measuring it could feed back.
			if (!props.inline && charWidth > 0 && el.clientWidth > 0) {
				const style = typeof getComputedStyle === "function" ? getComputedStyle(el) : null
				const padding =
					(Number.parseFloat(style?.paddingLeft ?? "") || 0) +
					(Number.parseFloat(style?.paddingRight ?? "") || 0)
				const usable = el.clientWidth - padding - gutterCh.value * charWidth
				fits.value = Math.floor(usable / charWidth)
			}
			nextTick(() => {
				tallOverflow.value = el.scrollHeight > el.clientHeight + 1
				wideOverflow.value = el.scrollWidth > el.clientWidth + 1
			})
		}
		let unmounted = false
		onMounted(() => {
			measure()
			if (typeof ResizeObserver !== "undefined" && box.value) {
				observer = new ResizeObserver(() => measure())
				observer.observe(box.value)
			}
			// A web font that loads late changes the glyph width: measure again once fonts are in.
			if (typeof document !== "undefined" && document.fonts?.ready) {
				document.fonts.ready.then(() => !unmounted && measure()).catch(() => {})
			}
		})
		watch(
			() => [props.text, props.columns],
			() => nextTick(measure)
		)
		onBeforeUnmount(() => {
			unmounted = true
			observer?.disconnect()
		})

		function run(segment: CommandSegment, key: string): VNode | string {
			const trailing = "trailing" in segment && segment.trailing ? ` ${TRAILING_MARK}` : ""
			switch (segment.kind) {
				case "tab":
					return h(
						"span",
						{
							key,
							class: `talon-command-tab text-tertiary relative bg-[rgba(var(--info-color-rgb)/0.15)] before:absolute before:left-0 before:content-['→']${trailing}`,
							"data-testid": "talon-command-tab",
							title: "A tab"
						},
						segment.text
					)
				case "trailing":
					return h(
						"span",
						{
							key,
							class: `talon-command-trailing ${TRAILING_MARK}`,
							"data-testid": "talon-command-trailing",
							title: "Spaces at the end of the line"
						},
						segment.text
					)
				case "edge":
					return h(
						"span",
						{
							key,
							class: "talon-command-edge text-info rounded-sm bg-[rgba(var(--info-color-rgb)/0.15)]",
							"data-testid": "talon-command-edge",
							title: "A space, where the line wraps"
						},
						segment.text
					)
				case "spaces":
					return h(
						"span",
						{
							key,
							class: `talon-command-spaces text-info rounded-sm bg-[rgba(var(--info-color-rgb)/0.15)]${trailing}`,
							"data-testid": "talon-command-spaces",
							"data-count": segment.count,
							title: `${segment.count} spaces${segment.trailing ? " at the end of the line" : ""}`
						},
						segment.text
					)
				case "nonascii":
					return h(
						"span",
						{
							key,
							class: `talon-command-nonascii decoration-warning underline decoration-wavy${trailing}`,
							"data-testid": "talon-command-nonascii",
							title: "Characters outside ASCII"
						},
						segment.text
					)
				case "escape":
					return h(
						"span",
						{
							key,
							class: `text-warning rounded-sm bg-[rgba(var(--warning-color-rgb)/0.18)] px-0.5${trailing}`,
							"data-testid": "talon-untrusted-escape",
							title: "An invisible, look-alike or control character"
						},
						segment.text
					)
				default:
					return segment.text
			}
		}

		function lineRows(lineRows: CommandSegment[][], index: number) {
			const number = props.firstLineNumber + index
			const last = index === rows.value.length - 1
			return h(
				"span",
				{ key: index, class: "block", "data-testid": "talon-command-line", "data-line": number },
				lineRows.map((row, at) => {
					const runs: (VNode | string)[] = row.map((segment, k) => run(segment, `${index}-${at}-${k}`))
					// The line's newline: kept in the text, drawn by the rows themselves.
					if (!last && at === lineRows.length - 1) runs.push(h("span", { class: "hidden" }, "\n"))
					return h(
						"span",
						{
							key: at,
							class: props.inline
								? "talon-command-row block min-h-[1.375em]"
								: "talon-command-row before:text-tertiary relative block min-h-[1.375em] pl-[calc(var(--talon-gutter)+1.5ch)] before:absolute before:left-0 before:w-(--talon-gutter) before:text-right before:content-[attr(data-gutter)]",
							"data-testid": "talon-command-row",
							"data-gutter": props.inline ? undefined : at === 0 ? String(number) : "↪",
							"data-continued": at > 0 ? "true" : undefined,
							title: at > 0 ? `Line ${number}, continued` : undefined
						},
						runs
					)
				})
			)
		}

		return () => {
			const pre = h(
				props.inline ? "span" : "pre",
				{
					class: [
						"talon-command m-0 font-mono leading-snug whitespace-pre",
						props.inline ? "talon-command-inline block" : ""
					],
					dir: "ltr",
					style: {
						unicodeBidi: "isolate",
						tabSize: 4,
						"--talon-gutter": `${String(lastNumber.value).length}ch`
					},
					"data-testid": props.testId,
					"data-columns": columns.value
				},
				rows.value.map(lineRows)
			)
			const measurer = h(
				"span",
				{
					ref: probe,
					"aria-hidden": "true",
					"data-probe": "true",
					class: "pointer-events-none invisible absolute top-0 left-0 font-mono whitespace-pre"
				},
				"0000000000"
			)
			const children: VNode[] = [
				h(
					props.inline ? "span" : "div",
					{
						ref: box,
						class: props.inline
							? "relative block overflow-x-auto"
							: "bg-default relative overflow-auto rounded p-1.5 text-xs",
						style: props.inline ? undefined : { maxHeight: `calc(${props.maxRows} * 1.375em + 0.75rem)` },
						"data-testid": `${props.testId}-box`
					},
					props.inline ? [pre] : [measurer, pre]
				)
			]
			if (scrolls.value) {
				const total = props.totalLines || lines.value.length
				children.push(
					h(
						"span",
						{ class: "text-warning block text-xs", "data-testid": `${props.testId}-scroll-cue` },
						`${total} ${total === 1 ? "line" : "lines"}, scroll to see all`
					)
				)
			}
			if (wideOverflow.value) {
				children.push(
					h(
						"span",
						{ class: "text-warning block text-xs", "data-testid": `${props.testId}-sideways-cue` },
						"A line is wider than the box: scroll sideways to see all of it."
					)
				)
			}
			return h(props.inline ? "span" : "div", { class: "flex min-w-0 flex-col gap-0.5" }, children)
		}
	}
})
