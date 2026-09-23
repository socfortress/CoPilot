<template>
	<ActivityRow rail-class="bg-border" :interactive="false">
		<!--
			Each box has the height of the text line it stands in for (see ActivityListItem):
			title 20px (text-sm), detail 18px per line (text-xs, leading-normal), meta and time 16px.
		-->
		<div class="flex h-5 items-center">
			<n-skeleton :height="12" :width="titleWidth" :sharp="false" />
		</div>

		<div v-if="detailLines" class="flex flex-col">
			<div v-for="line of detailLines" :key="line" class="flex h-4.5 items-center">
				<n-skeleton :height="9" :width="line === detailLines ? '64%' : '96%'" :sharp="false" />
			</div>
		</div>

		<div class="flex h-4 items-center gap-2">
			<n-skeleton :height="9" :width="42" :sharp="false" />
			<n-skeleton :height="9" :width="metaWidth" :sharp="false" />
		</div>

		<template #aside>
			<div class="flex h-4 items-center">
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
