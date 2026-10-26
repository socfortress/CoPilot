<template>
	<n-popconfirm
		:disabled="inProgress || requesting"
		:positive-text="hasAnalysis ? $t('alerts.aiRequest.runAgain') : $t('alerts.aiRequest.run')"
		:negative-text="$t('common.actions.cancel')"
		@positive-click="emit('request')"
	>
		<template #trigger>
			<n-button
				size="small"
				:type="hasAnalysis ? 'default' : 'primary'"
				:secondary="hasAnalysis"
				:disabled="inProgress"
				:loading="requesting"
				data-testid="ai-request-button"
			>
				<template #icon>
					<Icon v-if="inProgress" name="carbon:in-progress" />
					<Icon v-else-if="hasAnalysis" name="carbon:renew" />
					<Icon v-else name="carbon:ai-launch" />
				</template>
				{{ label }}
			</n-button>
		</template>
		<div class="max-w-72" data-testid="ai-request-confirm">
			{{ hasAnalysis ? $t("alerts.aiRequest.confirmAgain") : $t("alerts.aiRequest.confirm") }}
		</div>
	</n-popconfirm>
</template>

<script setup lang="ts">
// "Run AI analysis" on an alert's AI Report tab (#1215): confirms first, since every
// analysis counts, and stays disabled while one is under way.
import { NButton, NPopconfirm } from "naive-ui"
import { computed } from "vue"
import { useI18n } from "vue-i18n"
import Icon from "@/components/common/Icon.vue"

const { hasAnalysis, inProgress, requesting } = defineProps<{
	hasAnalysis: boolean
	inProgress: boolean
	requesting: boolean
}>()

const emit = defineEmits<{ request: [] }>()

const { t } = useI18n()

const label = computed(() => {
	if (inProgress) return t("alerts.aiRequest.inProgress")
	return hasAnalysis ? t("alerts.aiRequest.rerun") : t("alerts.aiRequest.runAi")
})
</script>
