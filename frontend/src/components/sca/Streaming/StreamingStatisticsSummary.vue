<template>
	<div v-if="stats" class="@container flex flex-col gap-4">
		<div class="grid grid-cols-1 gap-3 @xl:grid-cols-2 @4xl:grid-cols-3 @7xl:grid-cols-6">
			<CardLink
				v-for="tile of statTiles"
				:key="tile.id"
				size="small"
				:title="tile.title"
				:value="tile.value"
				:subtitle="tile.subtitle"
				:icon-left="tile.iconLeft"
				:color="tile.color"
			/>
		</div>

		<div class="grid grid-cols-1 gap-4 @lg:grid-cols-2">
			<CardStatsBars
				title="Check results"
				class="min-w-0"
				:values="checkResultValues"
				show-zero-items
				:show-total="false"
			/>
			<CardStatsBars
				title="Agent collection"
				class="min-w-0"
				:values="agentCollectionValues"
				show-zero-items
				:show-total="false"
			/>
		</div>

		<CardEntity size="small" embedded>
			<template #default>
				<div class="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
					<div class="flex flex-wrap items-center gap-1.5">
						<Badge type="splitted" bright size="small">
							<template #label>Results</template>
							<template #value>{{ stats.total_results.toLocaleString() }}</template>
						</Badge>
						<Badge type="splitted" bright size="small" color="success">
							<template #label>Pass</template>
							<template #value>{{ passRateLabel }}</template>
						</Badge>
						<Badge v-if="stats.total_invalid > 0" type="splitted" bright size="small">
							<template #label>Invalid</template>
							<template #value>{{ stats.total_invalid.toLocaleString() }}</template>
						</Badge>
					</div>
					<span class="text-tertiary text-xs">·</span>
					<p class="text-secondary min-w-0 flex-1 truncate text-xs" :title="stats.message">
						{{ stats.message }}
					</p>
				</div>
			</template>
		</CardEntity>
	</div>
</template>

<script setup lang="ts">
import type { CardLinkColor } from "@/components/common/cards/CardLink.vue"
import type { ItemProps } from "@/components/common/cards/CardStatsBars.vue"
import type { ScaStreamComplete } from "@/types/sca.d"
import { computed } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CardLink from "@/components/common/cards/CardLink.vue"
import CardStatsBars from "@/components/common/cards/CardStatsBars.vue"

const props = defineProps<{
	stats: ScaStreamComplete
}>()

const AgentsIcon = "carbon:network-3"
const PolicyIcon = "carbon:document"
const ScoreIcon = "carbon:chart-line"
const ChecksIcon = "carbon:task"
const PassedIcon = "carbon:checkmark-filled"
const FailedIcon = "carbon:close-filled"

interface StatTile {
	id: string
	title: string
	value: string | number
	subtitle?: string
	iconLeft: string
	color?: CardLinkColor
}

const passRateLabel = computed(() => {
	if (!props.stats.total_checks) return "—"
	return `${Math.round((props.stats.total_passes / props.stats.total_checks) * 100)}%`
})

const averageScoreColor = computed((): CardLinkColor | undefined => {
	const score = props.stats.average_score
	if (score >= 80) return "success"
	if (score >= 60) return "warning"
	return "danger"
})

const statTiles = computed<StatTile[]>(() => {
	const s = props.stats

	return [
		{
			id: "agents",
			title: "Total Agents",
			value: s.total_agents.toLocaleString(),
			subtitle: `${s.agents_successful.toLocaleString()} successful`,
			iconLeft: AgentsIcon,
			color: "primary"
		},
		{
			id: "policies",
			title: "Total Policies",
			value: s.total_policies.toLocaleString(),
			subtitle: `${s.total_results.toLocaleString()} policy rows`,
			iconLeft: PolicyIcon
		},
		{
			id: "score",
			title: "Average Score",
			value: `${s.average_score}%`,
			subtitle: "Across collected policies",
			iconLeft: ScoreIcon,
			color: averageScoreColor.value
		},
		{
			id: "checks",
			title: "Checks",
			value: s.total_checks.toLocaleString(),
			subtitle: "Total evaluated rules",
			iconLeft: ChecksIcon
		},
		{
			id: "passed",
			title: "Passed",
			value: s.total_passes.toLocaleString(),
			subtitle: passRateLabel.value !== "—" ? `${passRateLabel.value} pass rate` : "pass rate N/D",
			iconLeft: PassedIcon,
			color: "success"
		},
		{
			id: "failed",
			title: "Failed",
			value: s.total_fails.toLocaleString(),
			subtitle: `${s.agents_failed || 0} agent errors`,
			iconLeft: FailedIcon,
			color: "danger"
		}
	]
})

const checkResultValues = computed<ItemProps[]>(() => [
	{ label: "Passed", value: props.stats.total_passes, status: "success" },
	{ label: "Failed", value: props.stats.total_fails, status: "error" },
	{ label: "Invalid", value: props.stats.total_invalid, status: "muted" }
])

const agentCollectionValues = computed<ItemProps[]>(() => [
	{ label: "Processed", value: props.stats.agents_processed, status: "primary" },
	{ label: "Successful", value: props.stats.agents_successful, status: "success" },
	{ label: "Failed", value: props.stats.agents_failed, status: "error" }
])
</script>
