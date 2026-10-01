import axios from "axios"
import { getCurrentScope, onScopeDispose, ref } from "vue"

/**
 * Runs a list's load so that only the latest one counts.
 *
 * - starting a load aborts the one still in flight;
 * - `loading` is cleared in a `finally`, by the latest load only — a superseded load
 *   neither clears it (its successor is still running) nor reports its error;
 * - a load that is cancelled without a successor (`cancel()`, or the component going
 *   away) clears it too.
 *
 * The lists used to clear `loading` inside `try` and in a `catch` that skipped
 * cancellations, so a latest load that ended cancelled left the spinner on for good.
 */
export function useLatestRequest() {
	const loading = ref(false)
	let current: AbortController | null = null

	async function run(task: (signal: AbortSignal) => Promise<unknown>, onError?: (err: unknown) => void) {
		current?.abort()
		const controller = new AbortController()
		current = controller
		loading.value = true

		try {
			await task(controller.signal)
		} catch (err) {
			if (current === controller && !axios.isCancel(err)) onError?.(err)
		} finally {
			if (current === controller) {
				current = null
				loading.value = false
			}
		}
	}

	function cancel() {
		current?.abort()
		current = null
		loading.value = false
	}

	if (getCurrentScope()) onScopeDispose(cancel)

	return { loading, run, cancel }
}
