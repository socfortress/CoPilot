<template>
	<n-card content-class="p-0!" class="overflow-hidden" :class="{ 'hover:border-primary': hovered }">
		<div class="flex h-full flex-col overflow-hidden">
			<div class="border-default flex items-center justify-between gap-4 overflow-hidden border-b px-4 py-2.5">
				<div class="flex grow items-center gap-2 overflow-hidden text-base">
					<span class="truncate">{{ title }}</span>
					<Icon v-if="hovered" :name="ArrowRightIcon" :size="12" />
				</div>
				<div>
					<slot name="icon"></slot>
				</div>
			</div>
			<div class="divide-border flex grow divide-x">
				<div
					v-for="item of values"
					:key="JSON.stringify(item)"
					class="flex flex-1 flex-col overflow-hidden text-center"
					:class="values.length !== 1 ? `basis-1/${values.length}` : 'grow'"
				>
					<div
						class="font-display flex grow items-center justify-center truncate px-1.5 py-2.5 text-xl leading-none font-bold"
						:class="statusColorClass(item.status)"
					>
						{{ item.value }}
					</div>
					<div
						v-if="item.label"
						class="border-default bg-secondary truncate border-t p-1.5 font-mono text-xs leading-none uppercase"
						:class="item.status ? statusColorClass(item.status) : 'text-secondary'"
					>
						{{ item.label }}
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

export interface ItemProps {
	value: number | string
	label?: string
	status?: "success" | "warning" | "error"
}

const props = defineProps<{
	title: string
	values: ItemProps[]
	hovered?: boolean
}>()
const { title, values, hovered } = toRefs(props)

const ArrowRightIcon = "carbon:arrow-right"

function statusColorClass(status?: ItemProps["status"]) {
	switch (status) {
		case "success":
			return "text-success"
		case "warning":
			return "text-warning"
		case "error":
			return "text-error"
		default:
			return ""
	}
}
</script>
