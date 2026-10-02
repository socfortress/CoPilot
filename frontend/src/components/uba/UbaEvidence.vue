<template>
	<div class="flex flex-col gap-2">
		<n-button text size="tiny" type="primary" :loading @click="toggle">
			{{ open ? "Hide events" : count ? `Show events (${count})` : "Show events" }}
		</n-button>
		<template v-if="open">
			<UbaError v-if="error" :error />
			<template v-else-if="evidence">
				<p v-if="evidence.note" class="text-secondary text-xs">{{ evidence.note }}</p>
				<div v-for="event of evidence.events" :key="event.gl2_message_id" class="flex flex-col gap-1">
					<span class="text-tertiary font-mono text-xs">
						{{ event.timestamp ? formatDate(event.timestamp, dFormats.datetime) : "" }} · {{ event.index }}
					</span>
					<CodeSource :code="event.source" lang="json" :max-height="320" />
				</div>
				<p v-if="evidence.missing.length" class="text-tertiary text-xs">
					{{ evidence.missing.length }} event(s) no longer in the indexer (index retention):
					<span class="font-mono">{{ evidence.missing.join(", ") }}</span>
				</p>
			</template>
		</template>
	</div>
</template>

<script setup lang="ts">
// The source events behind one UBA finding, loaded from UBA (which reads the indexer) on first open.
import type { ApiError } from "@/types/common"
import type { UbaEvidence } from "@/types/uba"
import { NButton } from "naive-ui"
import { ref } from "vue"
import Api from "@/api"
import CodeSource from "@/components/common/CodeSource.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"
import UbaError from "./UbaError.vue"

const { customerCode, signalId, count = 0 } = defineProps<{ customerCode: string; signalId: string; count?: number }>()

const dFormats = useSettingsStore().dateFormat
const open = ref(false)
const loading = ref(false)
const error = ref<ApiError | null>(null)
const evidence = ref<UbaEvidence | null>(null)

function toggle() {
	open.value = !open.value
	if (!open.value || evidence.value || loading.value) return
	loading.value = true
	error.value = null
	Api.uba
		.getSignalEvidence(customerCode, signalId)
		.then(res => {
			evidence.value = res.data
		})
		.catch((err: ApiError) => {
			error.value = err
		})
		.finally(() => {
			loading.value = false
		})
}
</script>
