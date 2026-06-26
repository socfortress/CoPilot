<template>
	<n-card class="overflow-hidden" :class="{ 'hover:border-primary': hovered }">
		<div class="flex h-full items-center overflow-hidden">
			<div class="flex w-full gap-4 overflow-hidden" :class="{ 'flex-col items-center text-center': vertical }">
				<div class="flex flex-col justify-center">
					<slot name="icon"></slot>
				</div>
				<div class="info flex grow flex-col overflow-hidden">
					<div class="flex items-center gap-2 truncate text-base">
						{{ title }}
						<Icon v-if="hovered" :name="ArrowRightIcon" :size="12" />
					</div>
					<div v-if="value" class="font-display mt-1 truncate text-xl font-bold">
						{{ value }}
					</div>
				</div>
			</div>
		</div>
	</n-card>
</template>

<script setup lang="ts">
import { NCard } from "naive-ui"
import { toRefs } from "vue"
import Icon from "@/components/common/Icon.vue"

const props = defineProps<{
	title: string
	value?: number | string
	vertical?: boolean
	hovered?: boolean
}>()
const { title, value, vertical, hovered } = toRefs(props)

const ArrowRightIcon = "carbon:arrow-right"
</script>
