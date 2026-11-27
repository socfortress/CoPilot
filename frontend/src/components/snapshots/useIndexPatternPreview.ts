import { useDebounceFn } from "@vueuse/core"
import { onBeforeUnmount, ref, watch } from "vue"
import Api from "@/api"

export type IndexPatternPreviewState =
	| { kind: "idle" }
	| { kind: "checking" }
	| { kind: "problem"; problem: string }
	| { kind: "matches"; count: number; indices: string[]; truncated: boolean }
	| { kind: "unavailable" }

export const PREVIEW_DEBOUNCE_MS = 400

/**
 * Which indices `pattern` matches on the cluster right now, asked again whenever it changes.
 *
 * Typing is debounced, a check still running when the pattern changes is aborted, and an answer
 * for a pattern that is no longer the one in the field is dropped.
 */
export function useIndexPatternPreview(pattern: () => string | null | undefined) {
	const preview = ref<IndexPatternPreviewState>({ kind: "idle" })
	let controller: AbortController | null = null

	async function check(asked: string) {
		if (asked !== (pattern() ?? "")) return
		controller?.abort()
		const current = new AbortController()
		controller = current
		try {
			const { data } = await Api.snapshots.previewSchedulePattern(asked, current.signal)
			if (current.signal.aborted) return
			preview.value = data.problem
				? { kind: "problem", problem: data.problem }
				: {
						kind: "matches",
						count: data.matching_index_count ?? 0,
						indices: data.matching_indices ?? [],
						truncated: Boolean(data.truncated)
					}
		} catch {
			if (!current.signal.aborted) preview.value = { kind: "unavailable" }
		}
	}

	const checkSoon = useDebounceFn(check, PREVIEW_DEBOUNCE_MS)

	watch(
		pattern,
		value => {
			controller?.abort()
			if (!value?.trim()) {
				preview.value = { kind: "idle" }
				return
			}
			preview.value = { kind: "checking" }
			checkSoon(value)
		},
		{ immediate: true }
	)

	onBeforeUnmount(() => controller?.abort())

	return { preview }
}
