import type { Ref } from "vue"
import { onBeforeUnmount, ref, watch } from "vue"

/** The attribute that marks a part of the Knowledge pane the bar can jump to. */
export const ANCHOR_ATTR = "data-knowledge-anchor"

// While a jump scrolls smoothly past the parts in between, the bar keeps the one asked for.
const JUMP_HOLD_MS = 900

/**
 * Which part of the Knowledge pane is in view, and a jump to any of them.
 *
 * Parts are found by `data-knowledge-anchor` inside `root`, never by a page-wide id: the customer
 * page can be open in a modal over itself. The part in view is the first one, in order, crossing a
 * band in the upper part of the window. The page scrolls inside the layout's scrollbar, not the
 * window, so the observer watches the viewport and reads where each part is.
 */
export function useKnowledgeSpy(root: Readonly<Ref<HTMLElement | null>>, ids: Readonly<Ref<string[]>>) {
	const active = ref<string | null>(null)
	const visible = new Set<string>()
	let observer: IntersectionObserver | null = null
	let holdUntil = 0

	function anchor(id: string): HTMLElement | null {
		return root.value?.querySelector<HTMLElement>(`[${ANCHOR_ATTR}="${id}"]`) ?? null
	}

	function pick() {
		if (Date.now() < holdUntil) return
		const first = ids.value.find(id => visible.has(id))
		if (first) active.value = first
	}

	function observe() {
		observer?.disconnect()
		visible.clear()
		if (typeof IntersectionObserver === "undefined" || !root.value) return
		observer = new IntersectionObserver(
			entries => {
				for (const entry of entries) {
					const id = (entry.target as HTMLElement).getAttribute(ANCHOR_ATTR)
					if (!id) continue
					if (entry.isIntersecting) visible.add(id)
					else visible.delete(id)
				}
				pick()
			},
			{ rootMargin: "-20% 0px -60% 0px" }
		)
		for (const id of ids.value) {
			const el = anchor(id)
			if (el) observer.observe(el)
		}
	}

	function go(id: string) {
		const el = anchor(id)
		if (!el) return
		active.value = id
		holdUntil = Date.now() + JUMP_HOLD_MS
		const reduce = typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches
		el.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" })
	}

	/** Watch the parts again: call it once they are in the page (the bar's `mounted`). */
	function refresh() {
		if (!active.value || !ids.value.includes(active.value)) active.value = ids.value[0] ?? null
		observe()
	}

	watch([root, ids], refresh, { flush: "post", immediate: true })

	onBeforeUnmount(() => observer?.disconnect())

	return { active, go, refresh }
}
