<template>
	<CardEntity
		size="small"
		embedded
		hoverable
		clickable
		class="h-full"
		main-box-class="grow"
		card-entity-wrapper-class="h-full"
		header-box-class="flex-nowrap! items-start"
		:card-entity-class="priorityBorderClass"
	>
		<template #headerMain>
			<span class="text-default font-mono font-semibold">{{ item.cve }}</span>
		</template>

		<template #headerExtra>
			<div class="flex flex-wrap items-center justify-end gap-2">
				<PatchTuesdayPriorityBadge :priority="item.prioritization.priority" />
				<Badge v-if="item.kev.in_kev" type="splitted" bright color="danger" size="small">
					<template #label>
						<Icon :name="AlertIcon" :size="12" />
						KEV
					</template>
				</Badge>
				<Badge v-if="item.severity" type="splitted" bright :color="severityBadgeColor" size="small">
					<template #label>{{ item.severity }}</template>
				</Badge>
			</div>
		</template>

		<template #default>
			<div class="flex flex-col gap-3">
				<p class="line-clamp-2 text-sm leading-snug font-medium">
					{{ item.title || "No title available" }}
				</p>

				<div class="text-secondary flex min-w-0 flex-col gap-2 text-xs">
					<div class="flex min-w-0 items-center gap-2">
						<Icon :name="FamilyIcon" :size="14" class="shrink-0" />
						<span class="truncate" :title="item.affected.family">{{ item.affected.family }}</span>
					</div>
					<div class="flex min-w-0 items-center gap-2">
						<Icon :name="ProductIcon" :size="14" class="shrink-0" />
						<span class="truncate" :title="item.affected.product">{{ truncatedProduct }}</span>
					</div>
					<div v-if="item.affected.component_hint" class="flex min-w-0 items-center gap-2">
						<Icon :name="ComponentIcon" :size="14" class="shrink-0" />
						<span class="truncate font-mono">{{ item.affected.component_hint }}</span>
					</div>
				</div>
			</div>
		</template>

		<template #footerMain>
			<div class="flex flex-wrap items-center gap-2">
				<Badge v-if="item.cvss.base !== null" type="splitted" size="small" :color="cvssBadgeColor">
					<template #label>CVSS</template>
					<template #value>{{ item.cvss.base.toFixed(1) }}</template>
				</Badge>

				<Badge v-if="item.epss.score !== null" type="splitted" size="small" color="warning">
					<template #label>EPSS</template>
					<template #value>{{ (item.epss.score * 100).toFixed(1) }}%</template>
				</Badge>

				<Badge v-if="item.epss.percentile !== null" type="splitted" size="small" color="warning">
					<template #label>Percentile</template>
					<template #value>{{ (item.epss.percentile * 100).toFixed(0) }}%</template>
				</Badge>

				<Badge v-if="item.remediation.kbs.length > 0" type="splitted" size="small">
					<template #label>
						<Icon :name="LinkIcon" :size="12" />
						KB
					</template>
					<template #value>{{ kbSummary }}</template>
				</Badge>
			</div>
		</template>

		<template #footerExtra>
			<div class="text-tertiary flex min-w-0 items-center gap-1.5 text-xs">
				<Icon :name="ClockIcon" :size="14" class="shrink-0" />
				<span class="truncate" :title="item.prioritization.suggested_sla">
					{{ item.prioritization.suggested_sla }}
				</span>
			</div>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { BadgeColor } from "@/components/common/Badge.vue"
import type { PatchTuesdayItem } from "@/types/patchTuesday.d"
import { computed } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { PriorityLevel } from "@/types/patchTuesday.d"
import PatchTuesdayPriorityBadge from "./PatchTuesdayPriorityBadge.vue"

const { item } = defineProps<{
	item: PatchTuesdayItem
}>()

const AlertIcon = "carbon:warning"
const ClockIcon = "carbon:time"
const LinkIcon = "carbon:link"
const FamilyIcon = "carbon:category"
const ProductIcon = "carbon:cube"
const ComponentIcon = "carbon:chip"

const truncatedProduct = computed(() => {
	const product = item.affected.product
	if (product.length <= 48) return product
	return `${product.slice(0, 48)}…`
})

const kbSummary = computed(() => {
	const kbs = item.remediation.kbs
	if (kbs.length <= 2) return kbs.join(", ")
	return `${kbs.slice(0, 2).join(", ")} +${kbs.length - 2}`
})

const priorityBorderClass = computed(() => {
	switch (item.prioritization.priority) {
		case PriorityLevel.P0:
			return "border-error!"
		case PriorityLevel.P1:
			return "border-warning!"
		case PriorityLevel.P2:
			return "border-info!"
		case PriorityLevel.P3:
			return "border-success!"
		default:
			return "border-border!"
	}
})

const severityBadgeColor = computed((): BadgeColor | undefined => {
	const severity = item.severity?.toLowerCase()
	if (severity === "critical") return "danger"
	if (severity === "important") return "warning"
	if (severity === "low") return "success"
	return undefined
})

const cvssBadgeColor = computed((): BadgeColor | undefined => {
	const score = item.cvss.base
	if (score === null) return undefined
	if (score >= 9) return "danger"
	if (score >= 7) return "warning"
	if (score >= 4) return "primary"
	return "success"
})
</script>
