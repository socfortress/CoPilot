<template>
	<div class="grid grid-cols-1 gap-6 @xl:grid-cols-2 @3xl:grid-cols-3 @6xl:grid-cols-5">
		<CardStats title="Total Alerts">
			<template #icon>
				<Icon name="carbon:warning-alt" :size="24" class="text-error" />
			</template>
			<template #value>
				<div class="flex items-baseline gap-2">
					<div>
						{{ stats.totalAlerts }}
					</div>
					<div v-if="stats.alertTrend !== '0'" class="text-sm" :class="trendClass(stats.alertTrend)">
						{{ stats.alertTrend }}
					</div>
				</div>
			</template>
		</CardStats>

		<CardStats title="Critical Alerts" :value="stats.criticalAlerts">
			<template #icon>
				<Icon name="carbon:warning-diamond" :size="24" class="text-warning" />
			</template>
		</CardStats>

		<CardStats title="Open Cases" :value="stats.openCases">
			<template #icon>
				<Icon name="carbon:document" :size="24" class="text-info" />
			</template>
		</CardStats>

		<CardStats title="Security Score">
			<template #icon>
				<Icon name="carbon:security" :size="24" class="text-success" />
			</template>
			<template #value>
				<div class="flex items-baseline gap-2">
					<div>{{ stats.securityScore }}%</div>
					<div class="text-sm" :class="trendClass(`+${stats.scoreImprovement}`, true)">
						+{{ stats.scoreImprovement }}%
					</div>
				</div>
			</template>
		</CardStats>

		<CardStats title="Total Agents" :value="stats.totalAgents">
			<template #icon>
				<Icon name="carbon:network-3" :size="24" class="text-primary" />
			</template>
		</CardStats>
	</div>
</template>

<script setup lang="ts">
import CardStats from "@/components/common/cards/CardStats.vue"
import Icon from "@/components/common/Icon.vue"
import { trendClass } from "@/utils"

export interface Stats {
	totalAlerts: number
	criticalAlerts: number
	openCases: number
	totalAgents: number
	securityScore: number
	alertTrend: string
	scoreImprovement: number
}

defineProps<{
	stats: Stats
}>()
</script>
