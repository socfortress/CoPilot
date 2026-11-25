<template>
	<n-modal
		:show
		preset="card"
		:style="{ maxWidth: 'min(900px, 95vw)' }"
		:bordered="false"
		:title="`Noise report preview: ${customerCode ?? ''}`"
		segmented
		@update:show="emit('update:show', $event)"
	>
		<n-spin :show="loading" class="min-h-40">
			<div v-if="preview" class="flex flex-col gap-3 text-sm" data-testid="stats-preview">
				<n-alert type="info" :bordered="false" data-testid="stats-preview-nothing-sent">
					Nothing was sent. This is the report CoPilot would send for {{ preview.week }}.
				</n-alert>
				<div data-testid="stats-preview-would-send">
					<span v-if="preview.would_send.ok">Would be sent with the next run.</span>
					<span v-else>Would not be sent now: {{ preview.would_send.why }}</span>
				</div>
				<div v-if="preview.message && !preview.payload" class="text-secondary">{{ preview.message }}</div>
				<div class="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
					<span class="text-secondary">Pseudonym</span>
					<span class="font-mono break-all">{{ preview.customer_pseudonym }}</span>
					<template v-if="preview.payload_sha256">
						<span class="text-secondary">SHA-256</span>
						<span class="font-mono break-all" data-testid="stats-preview-sha256">{{ preview.payload_sha256 }}</span>
						<span class="text-secondary">Size</span>
						<span>{{ preview.payload_bytes }} bytes</span>
					</template>
					<span class="text-secondary">Patterns</span>
					<span>
						{{ preview.local.sent }} sent of {{ preview.local.raw_patterns }} found
						<template v-if="preview.local.merged">({{ preview.local.merged }} merged)</template>
						<template v-if="preview.local.truncated">, truncated</template>
					</span>
				</div>
				<div v-if="preview.local.unavailable_events?.length" class="text-warning" data-testid="stats-preview-unavailable">
					Left out: event {{ preview.local.unavailable_events.join(", ") }}, whose fields the indexer cannot aggregate in
					every index (see CoPilot's log).
				</div>
				<div v-if="drops.length" data-testid="stats-preview-drops">
					<div class="text-secondary mb-1">Left out, by reason</div>
					<div class="flex flex-wrap gap-1">
						<n-tag v-for="[reason, count] of drops" :key="reason" size="small">{{ reason }}: {{ count }}</n-tag>
					</div>
				</div>
				<n-scrollbar v-if="preview.payload" class="max-h-[50vh]">
					<pre class="bg-secondary rounded-sm p-2 font-mono text-xs" data-testid="stats-preview-payload">{{
						prettyPayload
					}}</pre>
				</n-scrollbar>
			</div>
		</n-spin>
	</n-modal>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { StatsPreview } from "@/types/sysmon-config"
import { NAlert, NModal, NScrollbar, NSpin, NTag, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"

const props = defineProps<{ show: boolean; customerCode: string | null }>()
const emit = defineEmits<{ (e: "update:show", value: boolean): void }>()

const message = useMessage()
const loading = ref(false)
const preview = ref<StatsPreview | null>(null)

// Rendered as text only: values in the payload are data, never markup
const prettyPayload = computed(() => (preview.value?.payload ? JSON.stringify(preview.value.payload, null, 2) : ""))
const drops = computed(() => Object.entries(preview.value?.local.dropped_by_reason ?? {}))

function load(code: string) {
	loading.value = true
	preview.value = null
	Api.sysmonConfig
		.previewStats(code)
		.then(res => {
			if (res.data.success) {
				preview.value = res.data.preview
			} else {
				message.error(res.data.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

watch(
	() => [props.show, props.customerCode] as const,
	([show, code]) => {
		if (show && code) load(code)
	},
	{ immediate: true }
)
</script>
