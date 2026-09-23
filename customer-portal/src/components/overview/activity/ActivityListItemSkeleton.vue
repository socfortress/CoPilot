<template>
	<ActivityRow rail-color="var(--border-color)" :interactive="false">
		<!-- Each box has the height of the text line it stands in for (see ActivityListItem). -->
		<div class="skeleton-line skeleton-line--title">
			<n-skeleton :height="12" :width="titleWidth" :sharp="false" />
		</div>

		<div v-if="detailLines" class="flex flex-col">
			<div v-for="line of detailLines" :key="line" class="skeleton-line skeleton-line--detail">
				<n-skeleton :height="9" :width="line === detailLines ? '64%' : '96%'" :sharp="false" />
			</div>
		</div>

		<div class="skeleton-line skeleton-line--meta gap-2">
			<n-skeleton :height="9" :width="42" :sharp="false" />
			<n-skeleton :height="9" :width="metaWidth" :sharp="false" />
		</div>

		<template #aside>
			<div class="skeleton-line skeleton-line--meta">
				<n-skeleton :height="9" :width="88" :sharp="false" />
			</div>
			<n-skeleton v-if="withAction" :height="ACTION_HEIGHT" :width="ACTION_WIDTH" :sharp="false" />
		</template>
	</ActivityRow>
</template>

<script setup lang="ts">
import { NSkeleton } from "naive-ui"
import ActivityRow from "./ActivityRow.vue"

const { detailLines = 0 } = defineProps<{
	titleWidth: string
	metaWidth: string
	detailLines?: number
	/** Reserve the space of the per-row details button. */
	withAction?: boolean
}>()

/** Size of AlertDetailsButton / CaseDetailsButton at size="tiny". */
const ACTION_WIDTH = 127
const ACTION_HEIGHT = 22
</script>

<style lang="scss" scoped>
.skeleton-line {
	display: flex;
	align-items: center;

	// title 14px × 1.35, detail 12px × 1.5, meta and time 16px
	&--title {
		height: 18.9px;
	}

	&--detail {
		height: 18px;
	}

	&--meta {
		height: 16px;
	}
}
</style>
