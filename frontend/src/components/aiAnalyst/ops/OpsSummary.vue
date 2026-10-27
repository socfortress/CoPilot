<template>
	<section
		class="flex flex-wrap items-center gap-x-4 gap-y-2"
		aria-label="Open findings at a glance"
		data-testid="talon-ops-summary"
	>
		<div v-if="loading && !summary" class="text-tertiary text-xs" data-testid="talon-ops-summary-loading">
			Counting open findings…
		</div>
		<p v-else-if="unsupported" class="text-tertiary text-xs" data-testid="talon-ops-summary-unsupported">
			This Talon doesn't count its findings yet: upgrade talon-analyst for the summary.
		</p>
		<p v-else-if="failure" class="text-tertiary text-xs" data-testid="talon-ops-summary-error">
			Couldn't count the open findings:
			<bdi>{{ failure.detail }}</bdi>
		</p>
		<template v-else-if="summary">
			<div class="flex flex-wrap items-center gap-1.5" role="group" aria-label="Open findings by severity">
				<n-tag
					v-for="chip of severityChips(summary.open)"
					:key="chip.value"
					:type="chip.tag"
					size="small"
					:bordered="severity === chip.value"
					:checkable="false"
					class="cursor-pointer"
					role="button"
					tabindex="0"
					:aria-pressed="severity === chip.value"
					:title="`Show the open ${chip.label.toLowerCase()} findings`"
					:data-testid="`talon-ops-summary-severity-${chip.value}`"
					@click="emit('severity', chip.value)"
					@keydown.enter.prevent="emit('severity', chip.value)"
					@keydown.space.prevent="emit('severity', chip.value)"
				>
					{{ chip.label }} {{ chip.count }}
				</n-tag>
				<n-tooltip v-if="summary.open.stale">
					<template #trigger>
						<n-tag
							type="warning"
							size="small"
							:bordered="staleOnly"
							class="cursor-pointer"
							role="button"
							tabindex="0"
							:aria-pressed="staleOnly"
							aria-describedby="talon-ops-stale-filter-help"
							data-testid="talon-ops-summary-stale"
							@click="emit('stale')"
							@keydown.enter.prevent="emit('stale')"
							@keydown.space.prevent="emit('stale')"
						>
							<template #icon><Icon name="carbon:warning-alt" :size="12" /></template>
							{{ summary.open.stale }} not measured
						</n-tag>
					</template>
					{{ STALE_FILTER_TEXT }}
				</n-tooltip>
				<span id="talon-ops-stale-filter-help" class="sr-only">{{ STALE_FILTER_TEXT }}</span>
			</div>

			<div
				v-if="customers.length"
				class="flex flex-wrap items-center gap-1.5"
				role="group"
				aria-label="Customers with the most open findings"
			>
				<span class="text-secondary text-xs">Top customers</span>
				<n-tag
					v-for="row of customers"
					:key="row.customer_code ?? ''"
					size="small"
					:bordered="isActiveCustomer(row.customer_code)"
					class="cursor-pointer"
					role="button"
					tabindex="0"
					:aria-pressed="isActiveCustomer(row.customer_code)"
					:data-testid="`talon-ops-summary-customer-${row.customer_code ?? 'platform'}`"
					@click="emit('customer', row.customer_code)"
					@keydown.enter.prevent="emit('customer', row.customer_code)"
					@keydown.space.prevent="emit('customer', row.customer_code)"
				>
					<bdi>{{ customerText(row.customer_code) }}</bdi>
					{{ row.total }}
				</n-tag>
			</div>

			<span
				v-if="summary.acknowledged !== null || summary.muted !== null"
				class="text-tertiary text-xs"
				data-testid="talon-ops-summary-acted"
			>
				{{ summary.acknowledged ?? "?" }} acknowledged · {{ summary.muted ?? "?" }} muted
			</span>
			<span v-if="summary.withheld" class="text-tertiary text-xs" data-testid="talon-ops-summary-withheld">
				Counted from your customers' rows only; some of Talon's counts couldn't be shown.
			</span>
		</template>
	</section>
</template>

<script setup lang="ts">
// The strip above the findings table (`GET /talon/ops/summary`): the open findings by severity, how
// many their job couldn't measure lately, the customers with the most, and how many are acknowledged or
// muted. A severity chip filters the table by that severity (open findings); the stale chip filters the
// rows already loaded (Talon has no stale filter: the tooltip says so); a customer chip filters by that
// customer (the platform one, by platform findings). Every value is text.
import type { TalonOpsFailure } from "@/api/endpoints/talonOps"
import type { TalonOpsSeverity, TalonOpsSummary } from "@/types/talonOps"
import { NTag, NTooltip } from "naive-ui"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"
import { customerText, severityChips, STALE_FILTER_TEXT, topCustomers } from "./ops"

const {
	summary = null,
	loading = false,
	failure = null,
	severity = null,
	staleOnly = false,
	customer = null,
	platform = false
} = defineProps<{
	summary?: TalonOpsSummary | null
	loading?: boolean
	failure?: TalonOpsFailure | null
	severity?: TalonOpsSeverity | null
	staleOnly?: boolean
	customer?: string | null
	platform?: boolean
}>()
const emit = defineEmits<{
	(e: "severity", value: TalonOpsSeverity): void
	(e: "stale"): void
	(e: "customer", code: string | null): void
}>()

const customers = computed(() => topCustomers(summary?.by_customer))
// A Talon before the summary answers 404 for it: the strip says so quietly; the table still works.
const unsupported = computed(() => failure?.code === "unsupported")

function isActiveCustomer(code: string | null): boolean {
	return code === null ? platform : !platform && customer === code
}
</script>
