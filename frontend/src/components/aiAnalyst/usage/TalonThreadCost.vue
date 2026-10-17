<template>
	<span
		v-if="usage"
		class="text-tertiary cursor-default font-mono text-xs"
		:title="
			usage.total.cost_complete
				? 'Talon cost of this thread so far (USD)'
				: 'Talon cost of this thread so far (USD); incomplete: some responses had no price'
		"
		data-testid="talon-v2-thread-cost"
	>
		{{ usage.total.cost_usd }} USD{{ usage.total.cost_complete ? "" : "+" }}
	</span>
</template>

<script setup lang="ts">
// The v2 conversation header's thread total (optional in the M5-9b plan): `GET
// /api/talon/v2/usage/threads/{id}`, the owner's only (talon-analyst refuses anyone else). The API's
// decimal string as it came. Read when the thread opens and after each completed turn; any failure
// shows nothing, so the header is as before.
import type { TalonThreadUsage } from "@/types/talonUsage"
import { onBeforeUnmount, ref, watch } from "vue"
import Api from "@/api"

const { threadId, refreshKey = 0 } = defineProps<{ threadId: string; refreshKey?: number }>()

const usage = ref<TalonThreadUsage | null>(null)
let controller: AbortController | null = null

async function load(id: string, keep: boolean) {
	controller?.abort()
	const own = new AbortController()
	controller = own
	if (!keep) usage.value = null
	try {
		const res = await Api.talonUsage.getThreadUsage(id, own.signal)
		if (controller === own) usage.value = res.data?.total ? res.data : null
	} catch {
		if (controller === own && !own.signal.aborted) usage.value = null
	}
}

watch(
	() => threadId,
	id => load(id, false),
	{ immediate: true }
)
watch(
	() => refreshKey,
	() => load(threadId, true)
)
onBeforeUnmount(() => controller?.abort())
</script>
