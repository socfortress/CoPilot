<script setup lang="ts">
// Bridges `@shuffleio/shuffle-mcps`'s internal toast facade onto Naive
// UI's message API so toasts the package emits (auth saved, test
// connection results, errors, etc.) surface in CoPilot's UI instead of
// the package's silent console.warn fallback.
import { setToastImpl } from "@shuffleio/shuffle-mcps"
import { useMessage } from "naive-ui"
import { onMounted } from "vue"

const message = useMessage()

function optsVariant(opts?: { description?: string; [key: string]: unknown }) {
	const v = opts?.variant
	return typeof v === "string" ? v : undefined
}

function emitToast(text: string, variant?: string) {
	if (!text) return
	switch (variant) {
		case "destructive":
		case "error":
			message.error(text)
			break
		case "success":
			message.success(text)
			break
		case "warning":
			message.warning(text)
			break
		default:
			message.info(text)
	}
}

onMounted(() => {
	setToastImpl((arg, opts) => {
		if (typeof arg === "string") {
			const text = opts?.description ? (arg ? `${arg} — ${opts.description}` : opts.description) : arg
			emitToast(text, optsVariant(opts) ?? "default")
			return
		}
		const title = arg.title
		const description = arg.description ?? opts?.description
		const text = description ? (title ? `${title} — ${description}` : description) : (title ?? "")
		const variant = arg.variant ?? optsVariant(opts)
		emitToast(text, variant ?? "default")
	})
})
</script>
