<template>
	<div class="grid grid-cols-1 gap-6 @xl:grid-cols-2 @4xl:grid-cols-4">
		<CardStats title="Total" :value="stats.total">
			<template #icon>
				<Icon :name="ICONS.alerts" :size="24" class="text-info" />
			</template>
		</CardStats>

		<CardStats title="Open" :value="stats.open">
			<template #icon>
				<Icon name="carbon:warning" :size="24" class="text-error" />
			</template>
		</CardStats>

		<CardStats title="In Progress" :value="stats.in_progress">
			<template #icon>
				<Icon name="carbon:hourglass" :size="24" class="text-warning" />
			</template>
		</CardStats>

		<CardStats title="Closed" :value="stats.closed">
			<template #icon>
				<Icon name="carbon:checkmark-outline" :size="24" class="text-success" />
			</template>
		</CardStats>
	</div>
</template>

<script setup lang="ts">
import CardStats from "@/components/common/cards/CardStats.vue"
import Icon from "@/components/common/Icon.vue"
import { ICONS } from "@/const"

export interface Stats {
	total: number
	open: number
	in_progress: number
	closed: number
}

defineProps<{
	stats: Stats
}>()
</script>
