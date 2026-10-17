import type { TextSegment } from "./approvals"
import { computed, defineComponent, h } from "vue"
import { linkSegments, safeSegments } from "./approvals"

/**
 * One untrusted value of a proposal (the model's reason, a comment, an argument, a host name, a
 * customer code, CoPilot's state text...), as text inside `<bdi>`, so its direction can't reorder
 * what is around it. Invisible and direction-changing characters are shown as `⟨U+202E⟩`. With
 * `links`, links are highlighted `<span>`s, never `<a>` (no `href`, nothing fetched), their hosts in
 * punycode.
 */
export default defineComponent({
	name: "TalonUntrusted",
	props: {
		text: { type: String, default: "" },
		links: { type: Boolean, default: false }
	},
	setup(props) {
		const segments = computed<TextSegment[]>(() =>
			props.links ? linkSegments(props.text) : safeSegments(props.text)
		)
		return () =>
			h(
				"bdi",
				{ class: "talon-untrusted", style: { unicodeBidi: "isolate" } },
				segments.value.map((segment, index) => {
					if (segment.kind === "escape") {
						return h(
							"span",
							{
								key: index,
								class: "text-warning rounded-sm bg-[rgba(var(--warning-color-rgb)/0.18)] px-0.5 font-mono text-[0.9em]",
								"data-testid": "talon-untrusted-escape",
								title: "An invisible or direction-changing character"
							},
							segment.text
						)
					}
					if (segment.kind === "link") {
						return h(
							"span",
							{
								key: index,
								class: "rounded-sm bg-[rgba(var(--warning-color-rgb)/0.18)] px-0.5 underline decoration-dotted",
								"data-testid": "talon-untrusted-link",
								title: segment.punycode
									? "A link, not opened; its host is shown in punycode"
									: "A link, not opened"
							},
							segment.text
						)
					}
					return segment.text
				})
			)
	}
})
