import type { VNode } from "vue"
import type { CommandSegment } from "./approvals"
import { computed, defineComponent, h, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue"
import { commandSegments, WRAP_COLUMNS, wrapSegments } from "./approvals"

const TRAILING_MARK =
	"bg-[rgba(var(--warning-color-rgb)/0.35)] outline-1 outline-[rgba(var(--warning-color-rgb)/0.7)] outline-dashed"

/**
 * A command exactly as it would run (talon-analyst's endpoint actions plan, EA-4): text nodes,
 * never HTML, Markdown or links, and every character visible without scrolling sideways.
 *
 * - Each line is numbered in a gutter, and a line longer than `WRAP_COLUMNS` is cut into rows, every
 *   row after the first marked `↪` in the gutter (the CSS wraps anything still too wide, too).
 * - Tabs keep the tab character and are marked by CSS; four or more spaces in a row are shown as
 *   `␠×N`; whitespace that ends a line is highlighted; non-ASCII runs are highlighted; a character
 *   nobody can see is shown as `⟨U+000D⟩` (`approvals.ts:commandSegments`).
 * - The box scrolls up and down only, and says "N lines, scroll to see all" when it holds more than
 *   it shows, so the cue doesn't depend on the OS drawing a scrollbar.
 *
 * Gutter numbers and markers are CSS `content`, not text, so the `<pre>`'s text is the command but
 * for the escapes and `␠×N` marks. Rendered in code, not a template, so a template's own line
 * breaks can't reach the `<pre>`. `inline` renders the runs alone, for a parameter value.
 */
export default defineComponent({
	name: "TalonCommandText",
	props: {
		text: { type: String, default: "" },
		/** Rows the box shows before it scrolls. */
		maxRows: { type: Number, default: 16 },
		/** The number of the text's first line in the whole command (the confirm shows one line). */
		firstLineNumber: { type: Number, default: 1 },
		/** Lines in the whole command, for the scroll cue (the text's own by default). */
		totalLines: { type: Number, default: 0 },
		/** Runs only, no box, gutter or rows: a parameter value. */
		inline: { type: Boolean, default: false },
		testId: { type: String, default: "talon-command-text" }
	},
	setup(props) {
		const lines = computed<CommandSegment[][]>(() => commandSegments(props.text))
		const rows = computed(() => lines.value.map(line => wrapSegments(line, WRAP_COLUMNS)))
		const rowCount = computed(() => rows.value.reduce((sum, line) => sum + line.length, 0))
		const lastNumber = computed(() => props.firstLineNumber + lines.value.length - 1)
		const box = ref<HTMLElement | null>(null)
		const measuredOverflow = ref(false)
		const scrolls = computed(() => rowCount.value > props.maxRows || measuredOverflow.value)
		let observer: ResizeObserver | null = null

		function measure() {
			const el = box.value
			measuredOverflow.value = !!el && el.scrollHeight > el.clientHeight + 1
		}
		onMounted(() => {
			measure()
			if (typeof ResizeObserver !== "undefined" && box.value) {
				observer = new ResizeObserver(measure)
				observer.observe(box.value)
			}
		})
		watch(
			() => props.text,
			() => nextTick(measure)
		)
		onBeforeUnmount(() => observer?.disconnect())

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
				case "spaces":
					return h(
						"span",
						{
							key,
							class: `talon-command-spaces text-info rounded-sm bg-[rgba(var(--info-color-rgb)/0.15)] px-0.5${trailing}`,
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

		return () => {
			if (props.inline) {
				return h(
					"span",
					{
						class: "talon-command-inline font-mono break-all whitespace-break-spaces",
						dir: "ltr",
						style: { unicodeBidi: "isolate", tabSize: 4 },
						"data-testid": props.testId
					},
					lines.value.flatMap((line, index) => {
						const runs = line.map((segment, at) => run(segment, `${index}-${at}`))
						return index < lines.value.length - 1 ? [...runs, "\n"] : runs
					})
				)
			}
			const pre = h(
				"pre",
				{
					class: "talon-command m-0 font-mono leading-snug break-all whitespace-break-spaces",
					dir: "ltr",
					style: {
						unicodeBidi: "isolate",
						tabSize: 4,
						"--talon-gutter": `${String(lastNumber.value).length}ch`
					},
					"data-testid": props.testId
				},
				rows.value.map((lineRows, index) => {
					const number = props.firstLineNumber + index
					const last = index === rows.value.length - 1
					return h(
						"span",
						{ key: index, class: "block", "data-testid": "talon-command-line", "data-line": number },
						lineRows.map((row, at) => {
							const runs: (VNode | string)[] = row.map((segment, k) =>
								run(segment, `${index}-${at}-${k}`)
							)
							// The line's newline: kept in the text, drawn by the rows themselves.
							if (!last && at === lineRows.length - 1) runs.push(h("span", { class: "hidden" }, "\n"))
							return h(
								"span",
								{
									key: at,
									class: "talon-command-row before:text-tertiary relative block min-h-[1.375em] pl-[calc(var(--talon-gutter)+1.5ch)] before:absolute before:left-0 before:w-(--talon-gutter) before:text-right before:content-[attr(data-gutter)]",
									"data-testid": "talon-command-row",
									"data-gutter": at === 0 ? String(number) : "↪",
									"data-continued": at > 0 ? "true" : undefined,
									title: at > 0 ? `Line ${number}, continued` : undefined
								},
								runs
							)
						})
					)
				})
			)
			const children: VNode[] = [
				h(
					"div",
					{
						ref: box,
						class: "bg-default overflow-x-hidden overflow-y-auto rounded p-1.5 text-xs",
						style: { maxHeight: `calc(${props.maxRows} * 1.375em + 0.75rem)` },
						"data-testid": `${props.testId}-box`
					},
					[pre]
				)
			]
			if (scrolls.value) {
				const total = props.totalLines || lines.value.length
				children.push(
					h(
						"div",
						{ class: "text-warning text-xs", "data-testid": `${props.testId}-scroll-cue` },
						`${total} ${total === 1 ? "line" : "lines"}, scroll to see all`
					)
				)
			}
			return h("div", { class: "flex min-w-0 flex-col gap-0.5" }, children)
		}
	}
})
