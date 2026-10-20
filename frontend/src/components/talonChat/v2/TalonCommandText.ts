import type { CommandSegment } from "./approvals"
import { computed, defineComponent, h } from "vue"
import { commandSegments } from "./approvals"

/**
 * A command exactly as it would run (talon-analyst's endpoint actions plan, EA-4): a `<pre>` of text
 * nodes, never HTML, Markdown or links, every line kept and not wrapped (it scrolls). Tabs keep the
 * tab character and are marked with an arrow drawn by CSS (not text), the spaces that end a line are
 * highlighted, and a character nobody can see is shown as `⟨U+000D⟩`, so the text copied out of
 * the box is the command but for those escapes. Rendered in code, not a template, so the
 * template's own line breaks can't reach the `<pre>`.
 */
export default defineComponent({
	name: "TalonCommandText",
	props: {
		text: { type: String, default: "" },
		/** The `<pre>`'s classes: its height and scrolling are the caller's. */
		boxClass: { type: String, default: "" },
		testId: { type: String, default: "talon-command-text" }
	},
	setup(props) {
		const lines = computed<CommandSegment[][]>(() => commandSegments(props.text))

		function run(segment: CommandSegment, key: string) {
			switch (segment.kind) {
				case "tab":
					return h(
						"span",
						{
							key,
							class: "talon-command-tab text-tertiary relative bg-[rgba(var(--info-color-rgb)/0.15)] before:absolute before:left-0 before:content-['→']",
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
							class: "talon-command-trailing bg-[rgba(var(--warning-color-rgb)/0.35)] outline-1 outline-[rgba(var(--warning-color-rgb)/0.7)] outline-dashed",
							"data-testid": "talon-command-trailing",
							title: "Spaces at the end of the line"
						},
						segment.text
					)
				case "escape":
					return h(
						"span",
						{
							key,
							class: "text-warning rounded-sm bg-[rgba(var(--warning-color-rgb)/0.18)] px-0.5",
							"data-testid": "talon-untrusted-escape",
							title: "An invisible or control character"
						},
						segment.text
					)
				default:
					return segment.text
			}
		}

		return () =>
			h(
				"pre",
				{
					class: [
						"talon-command bg-default m-0 overflow-auto rounded p-1.5 font-mono text-xs leading-snug whitespace-pre",
						props.boxClass
					],
					dir: "ltr",
					style: { unicodeBidi: "isolate", tabSize: 4 },
					"data-testid": props.testId
				},
				lines.value.flatMap((line, index) => {
					const runs: (string | ReturnType<typeof h>)[] = line.map((segment, at) =>
						run(segment, `${index}-${at}`)
					)
					return index < lines.value.length - 1 ? [...runs, "\n"] : runs
				})
			)
	}
})
