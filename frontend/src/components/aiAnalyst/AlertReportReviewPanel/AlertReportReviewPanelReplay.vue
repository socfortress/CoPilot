<template>
	<div class="flex flex-col gap-6">
		<!-- Toolbar: mode banner + replay trigger -->
		<div class="flex flex-wrap items-start justify-between gap-3">
			<div v-if="existingReview" class="flex flex-col gap-2">
				<Badge type="splitted" bright color="success">
					<template #label>Already reviewed</template>
					<template #value>Editing your previous submission</template>
				</Badge>
				<span v-if="existingReview.updated_at" class="text-secondary text-sm">
					Last edited {{ formatDate(existingReview.updated_at, dFormats.datetime) }}
				</span>
				<span v-else class="text-secondary text-sm">
					Submitted {{ formatDate(existingReview.created_at, dFormats.datetime) }}
				</span>
			</div>
			<div v-else />
			<n-button size="small" @click="showReplayModal = true">
				<template #icon>
					<Icon :name="ReplayIcon" :size="14" />
				</template>
				Replay with different template
			</n-button>
		</div>

		<ReplayModal v-model:show="showReplayModal" :report @replayed="onReplayed" />
	</div>
</template>

<script setup lang="ts">
import type { AiAnalystReport, AiAnalystReview } from "@/types/aiAnalyst.d"
import { NButton, useMessage } from "naive-ui"
import { ref } from "vue"
import Badge from "@/components/common/Badge.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"
import ReplayModal from "./ReplayModal.vue"

defineProps<{
	report: AiAnalystReport
	existingReview: AiAnalystReview | null
}>()

const ReplayIcon = "carbon:restart"

const message = useMessage()

const dFormats = useSettingsStore().dateFormat

const showReplayModal = ref(false)

function onReplayed(_data: Record<string, unknown> | undefined) {
	// The new report is created asynchronously by Talon's callbacks. Surface a
	// pointer so the reviewer knows where to watch — they can switch to the
	// Jobs tab or come back after the run completes.
	message.success("Replay queued — check the Jobs tab for the new run", { duration: 6000 })
}
</script>
