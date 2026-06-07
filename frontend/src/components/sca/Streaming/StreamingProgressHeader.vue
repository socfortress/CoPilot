<template>
	<CardEntity v-if="isStreaming || streamComplete" size="small" embedded :status="cardStatus">
		<template #header>
			<div class="flex items-center justify-between gap-2">
				<div class="flex min-w-0 flex-1 items-center gap-2">
					<Icon :name="statusIcon" :size="16" :class="statusIconClass" />
					<span class="truncate text-sm">{{ statusMessage }}</span>
				</div>

				<div class="flex shrink-0 items-center gap-2">
					<n-button v-if="isStreaming" size="small" type="error" secondary @click="emit('stop')">
						<template #icon>
							<Icon :name="StopIcon" :size="14" />
						</template>
						Stop
					</n-button>
					<n-button
						v-if="streamComplete"
						size="small"
						type="primary"
						secondary
						:loading="isConnecting"
						@click="emit('start')"
					>
						<template #icon>
							<Icon :name="RefreshIcon" :size="14" />
						</template>
						Refresh
					</n-button>
				</div>
			</div>
		</template>

		<template #default>
			<n-progress
				type="line"
				:percentage="progress.percent_complete"
				:status="progressStatus"
				:height="8"
				:border-radius="4"
				processing
				:show-indicator="false"
			/>
		</template>

		<template #footer>
			<div class="flex flex-wrap items-center gap-1.5">
				<Badge type="splitted" bright size="small" color="success">
					<template #label>Agents</template>
					<template #value>{{ progress.successful }}/{{ progress.total }}</template>
				</Badge>
				<Badge v-if="progress.failed > 0" type="splitted" bright size="small" color="danger">
					<template #label>Failed</template>
					<template #value>{{ progress.failed }}</template>
				</Badge>
				<Badge type="splitted" bright size="small">
					<template #label>Processed</template>
					<template #value>{{ progress.processed.toLocaleString() }}</template>
				</Badge>
				<Badge type="splitted" bright size="small" color="primary">
					<template #label>Results</template>
					<template #value>{{ resultsCount.toLocaleString() }}</template>
				</Badge>
				<Badge type="splitted" bright size="small">
					<template #label>Progress</template>
					<template #value>{{ progress.percent_complete }}%</template>
				</Badge>
			</div>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { ScaStreamProgress } from "@/types/sca.d"
import { NButton, NProgress } from "naive-ui"
import { computed } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"

const props = defineProps<{
	isConnecting: boolean
	isStreaming: boolean
	streamComplete: boolean
	streamError: string | null
	progress: ScaStreamProgress
	statusMessage: string
	resultsCount: number
}>()

const emit = defineEmits<{
	(e: "start"): void
	(e: "stop"): void
}>()

const RefreshIcon = "carbon:renew"
const StopIcon = "carbon:stop"
const ErrorIcon = "carbon:warning"
const SuccessIcon = "carbon:checkmark-filled"
const StreamingIcon = "carbon:in-progress"

const cardStatus = computed(() => {
	if (props.streamError) return "error"
	if (props.streamComplete) return "success"
	if (props.isStreaming) return "warning"
	return undefined
})

const progressStatus = computed(() => {
	if (props.streamError) return "error"
	if (props.streamComplete) return "success"
	return "default"
})

const statusIcon = computed(() => {
	if (props.streamError) return ErrorIcon
	if (props.streamComplete) return SuccessIcon
	return StreamingIcon
})

const statusIconClass = computed(() => {
	if (props.streamError) return "text-error"
	if (props.streamComplete) return "text-success"
	return "text-primary"
})
</script>
