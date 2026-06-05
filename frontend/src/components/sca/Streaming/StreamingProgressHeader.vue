<template>
	<n-card v-if="isStreaming || streamComplete" class="mb-4">
		<div class="flex flex-col gap-4">
			<div class="flex items-center gap-4">
				<n-progress
					type="line"
					:percentage="progress.percent_complete"
					:status="streamError ? 'error' : streamComplete ? 'success' : 'default'"
					show-indicator
					class="grow"
				/>
				<n-button
					v-if="!isStreaming && !streamComplete"
					type="primary"
					:loading="isConnecting"
					@click="emit('start')"
				>
					<template #icon>
						<Icon :name="RefreshIcon" />
					</template>
					Load SCA Data
				</n-button>
				<n-button v-if="isStreaming" type="error" @click="emit('stop')">
					<template #icon>
						<Icon :name="StopIcon" />
					</template>
					Stop
				</n-button>
				<n-button v-if="streamComplete" @click="emit('start')">
					<template #icon>
						<Icon :name="RefreshIcon" />
					</template>
					Refresh
				</n-button>
			</div>

			<div class="flex items-center justify-between text-sm">
				<span class="text-secondary">{{ statusMessage }}</span>
				<div class="flex gap-4">
					<span>
						Agents:
						<code class="text-success">{{ progress.successful }}</code>
						/
						<code>{{ progress.total }}</code>
						<code v-if="progress.failed > 0" class="text-error ml-1">({{ progress.failed }} failed)</code>
					</span>
					<span>
						Results:
						<code>{{ resultsCount }}</code>
					</span>
				</div>
			</div>
		</div>
	</n-card>
</template>

<script setup lang="ts">
import type { ScaStreamProgress } from "@/types/sca.d"
import { NButton, NCard, NProgress } from "naive-ui"
import Icon from "@/components/common/Icon.vue"

defineProps<{
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

const RefreshIcon = "carbon:refresh"
const StopIcon = "carbon:stop"
</script>
