<template>
	<div class="pipe-title flex items-center gap-1" :class="{ warning: isWarning }">
		<n-tooltip placement="top-start" trigger="hover" v-if="isWarning">
			<template #trigger>
				<Icon :name="DangerIcon" :size="18"></Icon>
			</template>
			Open Info dialog to see errors
		</n-tooltip>
		<span>{{ pipeline?.title }}</span>
	</div>
</template>

<script setup lang="ts">
import { NTooltip } from "naive-ui"
import { computed, toRefs } from "vue"
import type { Pipeline } from "@/types/graylog/pipelines.d"
import Icon from "@/components/common/Icon.vue"

const props = defineProps<{ pipeline: Pipeline }>()
const { pipeline } = toRefs(props)

const DangerIcon = "majesticons:exclamation-line"

const isWarning = computed<boolean>(() => {
	return !!pipeline.value.errors
})
</script>

<style lang="scss" scoped>
.pipe-title {
	line-height: 1.1;

	&.warning {
		color: var(--secondary3-color);
	}
}
</style>
