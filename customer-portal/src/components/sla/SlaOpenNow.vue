<template>
	<section
		class="bg-default border-default divide-border grid grid-cols-2 divide-y rounded-lg border md:grid-cols-5 md:divide-x md:divide-y-0"
		data-testid="sla-open-now"
		aria-label="Open right now"
	>
		<div
			v-for="item of items"
			:key="item.key"
			class="flex min-w-0 flex-col gap-1 px-4 py-3"
			:class="{ 'col-span-2 sm:col-span-1': item.key === 'waiting' }"
			:data-testid="`sla-open-${item.key}`"
		>
			<span class="text-tertiary flex items-center gap-1.5 text-xs">
				<Icon :name="item.icon" :size="14" :class="item.iconClass" />
				{{ item.label }}
			</span>
			<div class="flex items-baseline justify-between gap-2">
				<span
					class="font-display text-xl font-semibold tabular-nums"
					:class="item.value ? item.valueClass : undefined"
					data-testid="sla-open-value"
				>
					{{ item.value }}
				</span>
				<span v-if="item.links && item.value" class="flex gap-2 text-xs">
					<RouterLink
						v-for="link of item.links"
						:key="link.label"
						:to="link.to"
						class="text-secondary hover:text-primary flex items-center gap-0.5 no-underline transition-colors"
						:data-testid="linkTestId(item, link.label)"
					>
						{{ link.label }}
						<Icon name="carbon:arrow-right" :size="12" />
					</RouterLink>
				</span>
			</div>
		</div>
	</section>
</template>

<script setup lang="ts">
import type { RouteLocationRaw } from "vue-router"
import type { SlaOpenNow } from "@/types/sla"
import { computed } from "vue"
import { RouterLink } from "vue-router"
import Icon from "@/components/common/Icon.vue"
import { ICONS } from "@/const"
import { WAITING_ON_CUSTOMER } from "@/utils/workflowStatus"

const { openNow } = defineProps<{
	openNow: SlaOpenNow
}>()

interface Item {
	key: string
	label: string
	icon: string
	iconClass?: string
	value: number
	/** Applied only while the value is not zero: a zero is never alarming. */
	valueClass?: string
	links?: { label: string; to: RouteLocationRaw }[]
}

/** `sla-open-alerts-view-all`, `sla-open-waiting-cases`, … */
function linkTestId(item: Item, label: string) {
	return `sla-open-${item.key}-${label.toLowerCase().replaceAll(" ", "-")}`
}

// What is open now, whatever the period: the SOC's queue for this customer, and what
// waits on the customer themselves — linked to both lists, filtered on that status.
const items = computed<Item[]>(() => [
	// "Open" here is every status but closed, and the lists filter on one status at a
	// time, so these open the whole list rather than a filter that would show fewer.
	{
		key: "alerts",
		label: "Open alerts",
		icon: ICONS.alerts,
		value: openNow.alerts,
		links: [{ label: "View all", to: { name: "AlertsList" } }]
	},
	{
		key: "cases",
		label: "Open cases",
		icon: ICONS.cases,
		value: openNow.cases,
		links: [{ label: "View all", to: { name: "CasesList" } }]
	},
	{
		key: "at-risk",
		label: "Due soon",
		icon: "carbon:hourglass",
		iconClass: "text-warning",
		value: openNow.at_risk,
		valueClass: "text-warning"
	},
	{
		key: "breached",
		label: "Past target",
		icon: "carbon:warning-alt-filled",
		iconClass: "text-error",
		value: openNow.breached,
		valueClass: "text-error"
	},
	{
		key: "waiting",
		label: "Waiting on you",
		icon: "carbon:user-follow",
		iconClass: "text-primary",
		value: openNow.waiting_on_you,
		valueClass: "text-primary",
		links: [
			{ label: "Alerts", to: { name: "AlertsList", query: { status: WAITING_ON_CUSTOMER } } },
			{ label: "Cases", to: { name: "CasesList", query: { status: WAITING_ON_CUSTOMER } } }
		]
	}
])
</script>
