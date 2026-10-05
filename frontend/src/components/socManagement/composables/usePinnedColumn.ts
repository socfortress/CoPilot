import type { MaybeElementRef } from "@vueuse/core"
import { useElementSize } from "@vueuse/core"
import { computed } from "vue"

/**
 * Whether a table may pin its first column: only while the box it sits in is at
 * least `minWidth` wide. Below that a pinned column eats the room the other columns
 * need to scroll in, so the whole table scrolls as one instead. Before the box is
 * measured (width 0) it pins, which is what a wide desktop layout wants.
 */
export function usePinnedColumn(box: MaybeElementRef, minWidth: number) {
	const { width } = useElementSize(box)
	return computed(() => width.value === 0 || width.value >= minWidth)
}
