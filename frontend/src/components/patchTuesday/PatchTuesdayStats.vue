<template>
	<div class="@container flex flex-col gap-4">
		<n-spin :show="loading">
			<div class="flex flex-col gap-4">
				<div class="grid grid-cols-1 gap-3 @md:grid-cols-2 @2xl:grid-cols-3 @6xl:grid-cols-5">
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

				<div v-if="summary" class="grid grid-cols-1 gap-4 @lg:grid-cols-2">
					<CardStatsBars
						title="By severity"
						class="min-w-0"
						:values="severityValues"
						show-zero-items
						:show-total="false"
					/>
					<CardStatsBars
						title="By product family"
						class="min-w-0"
						:values="familyValues"
						show-zero-items
						:show-total="false"
					/>
				</div>

				<CardEntity v-if="summary" size="small" embedded>
					<template #default>
						<div class="flex flex-wrap items-center gap-2">
							<Badge type="splitted" bright>
								<template #label>Cycle</template>
								<template #value>{{ summary.cycle }}</template>
							</Badge>
							<Badge type="splitted" bright>
								<template #label>Patch Tuesday</template>
								<template #value>{{ formatDate(summary.patch_tuesday_date, "MMM D, YYYY") }}</template>
							</Badge>
							<Badge type="splitted" bright>
								<template #label>Total records</template>
								<template #value>{{ summary.total_records.toLocaleString() }}</template>
							</Badge>
							<Badge type="splitted" bright>
								<template #label>Generated</template>
								<template #value>
									{{ formatDate(summary.generated_utc, "MMM D, YYYY HH:mm", { tz: true }) }}
								</template>
							</Badge>
						</div>
					</template>
				</CardEntity>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { CardLinkColor } from "@/components/common/cards/CardLink.vue"
import type { ItemProps } from "@/components/common/cards/CardStatsBars.vue"
import type { PatchTuesdaySummary } from "@/types/patchTuesday.d"
import { NSpin } from "naive-ui"
import { computed } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CardLink from "@/components/common/cards/CardLink.vue"
import CardStatsBars from "@/components/common/cards/CardStatsBars.vue"
import { formatDate } from "@/utils/format"

const props = defineProps<{
	summary: PatchTuesdaySummary | null
	loading?: boolean
}>()

const ShieldIcon = "carbon:security"
const AlertIcon = "carbon:warning"
const UrgentIcon = "carbon:warning-hex"
const InfoIcon = "carbon:information"
const CheckIcon = "carbon:checkmark-filled"

interface StatTile {
	id: string
	title: string
	value: string | number
	subtitle?: string
	iconLeft: string
	color?: CardLinkColor
}

const statTiles = computed<StatTile[]>(() => {
	const s = props.summary

	return [
		{
			id: "total",
			title: "Unique CVEs",
			value: s?.unique_cves ?? "-",
			subtitle: s ? `${s.total_records.toLocaleString()} total records` : undefined,
			iconLeft: ShieldIcon,
			color: "primary"
		},
		{
			id: "p0",
			title: "P0 Emergency",
			value: s?.by_priority?.P0 ?? 0,
			subtitle: "Patch within 72 hours",
			iconLeft: AlertIcon,
			color: "danger"
		},
		{
			id: "p1",
			title: "P1 High",
			value: s?.by_priority?.P1 ?? 0,
			subtitle: "Patch within 7 days",
			iconLeft: UrgentIcon,
			color: "warning"
		},
		{
			id: "p2",
			title: "P2 Medium",
			value: s?.by_priority?.P2 ?? 0,
			subtitle: "Patch within 30 days",
			iconLeft: InfoIcon
		},
		{
			id: "p3",
			title: "P3 Low",
			value: s?.by_priority?.P3 ?? 0,
			subtitle: "Next maintenance window",
			iconLeft: CheckIcon,
			color: "success"
		}
	]
})

const severityStatusByLabel: Record<string, ItemProps["status"]> = {
	Critical: "error",
	Important: "warning",
	Moderate: "muted",
	Low: "success"
}

const severityValues = computed<ItemProps[]>(() => {
	if (!props.summary?.by_severity) return []

	return Object.entries(props.summary.by_severity)
		.sort(([, a], [, b]) => b - a)
		.map(([label, value]) => ({
			label,
			value,
			status: severityStatusByLabel[label] ?? "muted"
		}))
})

const familyValues = computed<ItemProps[]>(() => {
	if (!props.summary?.by_family) return []

	return Object.entries(props.summary.by_family)
		.sort(([, a], [, b]) => b - a)
		.map(([label, value]) => ({
			label,
			value,
			status: "primary" as const
		}))
})
</script>
