import { setToastImpl } from "@shuffleio/shuffle-mcps"
import { useMessage } from "naive-ui"
import { onMounted } from "vue"

/**
 * Bridges `@shuffleio/shuffle-mcps`'s internal toast facade onto Naive
 * UI's message API so toasts the package emits (auth saved, test
 * connection results, errors, etc.) surface in CoPilot's UI instead of
 * the package's silent console.warn fallback.
 *
 * Must run inside the `<n-message-provider>` tree, hence its home here
 * in `GlobalListener` rather than in `App.vue`.
 */

const VARIANT_TO_METHOD = {
	destructive: "error",
	error: "error",
	success: "success",
	warning: "warning"
} as const

export function useShuffleToastBridge() {
	const message = useMessage()

	onMounted(() => {
		setToastImpl((arg, opts) => {
			const obj = typeof arg === "string" ? null : arg
			const title = obj ? obj.title : arg
			const description = obj?.description ?? opts?.description
			const text = [title, description].filter(Boolean).join(" — ")
			if (!text) return

			const variant = obj?.variant ?? opts?.variant
			const method = VARIANT_TO_METHOD[variant as keyof typeof VARIANT_TO_METHOD] ?? "info"
			message[method](text)
		})
	})
}
