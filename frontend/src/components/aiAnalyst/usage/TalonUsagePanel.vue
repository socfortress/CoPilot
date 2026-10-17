<template>
	<div class="flex flex-col gap-4" data-testid="talon-usage">
		<div class="flex flex-wrap items-end gap-3">
			<label class="flex flex-col gap-1">
				<span class="text-secondary text-xs">Days (UTC, both included)</span>
				<n-date-picker
					v-model:formatted-value="range"
					type="daterange"
					value-format="yyyy-MM-dd"
					:clearable="false"
					size="small"
					data-testid="talon-usage-range"
				/>
			</label>
			<label class="flex flex-col gap-1">
				<span class="text-secondary text-xs">Group by</span>
				<n-select
					v-model:value="groupBy"
					:options="USAGE_GROUP_BY"
					size="small"
					class="w-36"
					data-testid="talon-usage-group-by"
				/>
			</label>
			<label class="flex flex-col gap-1">
				<span class="text-secondary text-xs">Customer</span>
				<n-select
					v-model:value="customer"
					:options="customerOptions"
					:loading="customersLoading"
					placeholder="All your customers"
					clearable
					filterable
					size="small"
					class="w-64"
					data-testid="talon-usage-customer"
				/>
			</label>
			<n-button
				size="small"
				:loading
				:disabled="!!rangeProblem"
				data-testid="talon-usage-refresh"
				@click="load()"
			>
				Refresh
			</n-button>
		</div>

		<p v-if="rangeProblem" class="text-error text-sm" data-testid="talon-usage-range-problem">{{ rangeProblem }}</p>
		<p v-if="!isAdmin" class="text-secondary text-sm" data-testid="talon-usage-scope-note">
			{{ NON_ADMIN_USAGE_NOTE }}
		</p>

		<n-alert v-if="failure" type="error" :bordered="false" size="small" data-testid="talon-usage-error">
			{{ failure.detail }}
		</n-alert>

		<n-spin :show="loading">
			<div v-if="report" class="flex flex-col gap-4">
				<div v-if="!report.total.cost_complete || report.truncated" class="flex flex-wrap gap-2">
					<n-tag
						v-if="!report.total.cost_complete"
						type="warning"
						size="small"
						data-testid="talon-usage-incomplete"
					>
						Incomplete: {{ formatCount(report.total.unpriced_responses) }} response(s) had no price, so the
						cost is a lower bound
					</n-tag>
					<n-tag v-if="report.truncated" type="info" size="small" data-testid="talon-usage-truncated">
						Truncated: the first {{ formatCount(report.groups.length) }} groups are listed; the total covers
						every row
					</n-tag>
				</div>

				<TalonUsageChart v-if="report.groups.length" :report />

				<n-table v-if="report.groups.length" size="small" :bordered="false" data-testid="talon-usage-table">
					<thead>
						<tr>
							<th>{{ groupByLabel }}</th>
							<th class="text-right">Responses</th>
							<th class="text-right">Input tokens</th>
							<th class="text-right">Output tokens</th>
							<th class="text-right">Cache read</th>
							<th class="text-right">Cache write</th>
							<th class="text-right">Cost (USD)</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="(group, index) of report.groups" :key="index" data-testid="talon-usage-row">
							<td data-testid="talon-usage-group">{{ usageGroupLabel(group, report.group_by) }}</td>
							<td class="text-right font-mono">{{ formatCount(group.responses) }}</td>
							<td class="text-right font-mono">{{ formatCount(group.input_tokens) }}</td>
							<td class="text-right font-mono">{{ formatCount(group.output_tokens) }}</td>
							<td class="text-right font-mono">{{ formatCount(group.cache_read_tokens) }}</td>
							<td class="text-right font-mono">{{ formatCount(group.cache_write_tokens) }}</td>
							<td class="text-right">
								<span class="font-mono" data-testid="talon-usage-cost">{{ group.cost_usd }}</span>
								<n-tag
									v-if="!group.cost_complete"
									type="warning"
									size="tiny"
									class="ml-2"
									data-testid="talon-usage-row-incomplete"
								>
									incomplete
								</n-tag>
							</td>
						</tr>
					</tbody>
					<tfoot>
						<tr class="font-semibold" data-testid="talon-usage-total">
							<td>Total</td>
							<td class="text-right font-mono">{{ formatCount(report.total.responses) }}</td>
							<td class="text-right font-mono">{{ formatCount(report.total.input_tokens) }}</td>
							<td class="text-right font-mono">{{ formatCount(report.total.output_tokens) }}</td>
							<td class="text-right font-mono">{{ formatCount(report.total.cache_read_tokens) }}</td>
							<td class="text-right font-mono">{{ formatCount(report.total.cache_write_tokens) }}</td>
							<td class="text-right">
								<span class="font-mono" data-testid="talon-usage-total-cost">
									{{ report.total.cost_usd }}
								</span>
							</td>
						</tr>
					</tfoot>
				</n-table>

				<n-empty
					v-else
					description="No Talon usage in this range"
					class="py-10"
					data-testid="talon-usage-empty"
				/>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
// The AI Analyst page's Usage tab (talon-analyst FR-COST-5, CoPilot M5-9b): Talon's tokens and cost
// per group over whole UTC days, from `GET /api/talon/v2/usage`. Only mounted with "Talon v2" on.
//
// Every cost is the API's decimal string, shown as it came: the total is the API's own total row,
// never a sum made here. The customer starts from the global filter and follows it (live sync);
// emptied, it means all of the caller's customers.
import type { TalonFailure } from "@/api/endpoints/talonUsage"
import type { TalonUsageGroupBy, TalonUsageReport } from "@/types/talonUsage"
import { NAlert, NButton, NDatePicker, NEmpty, NSelect, NSpin, NTable, NTag } from "naive-ui"
import { computed, onBeforeUnmount, ref, watch } from "vue"
import Api from "@/api"
import { talonFailure } from "@/api/endpoints/talonUsage"
import { useCustomerOptions } from "@/composables/useCustomerOptions"
import { useGlobalCustomerFilter } from "@/composables/useGlobalCustomerFilter"
import { useAuthStore } from "@/stores/auth"
import TalonUsageChart from "./TalonUsageChart.vue"
import {
	defaultUsageRange,
	formatCount,
	NON_ADMIN_USAGE_NOTE,
	USAGE_GROUP_BY,
	usageGroupLabel,
	usageRangeProblem
} from "./usage"

const isAdmin = computed(() => useAuthStore().isAdmin)
const { globalCustomerCode, onGlobalCustomerFilterChange } = useGlobalCustomerFilter()
const { options: customerOptions, loading: customersLoading, load: loadCustomers } = useCustomerOptions()

const range = ref<[string, string] | null>(defaultUsageRange())
const groupBy = ref<TalonUsageGroupBy>("customer")
const customer = ref<string | null>(globalCustomerCode.value)

const report = ref<TalonUsageReport | null>(null)
const failure = ref<TalonFailure | null>(null)
const loading = ref(false)
let controller: AbortController | null = null

const rangeProblem = computed(() => usageRangeProblem(range.value?.[0], range.value?.[1]))
const groupByLabel = computed(() => USAGE_GROUP_BY.find(o => o.value === groupBy.value)?.label ?? "Group")

async function load() {
	controller?.abort()
	if (rangeProblem.value || !range.value) {
		report.value = null
		failure.value = null
		loading.value = false
		return
	}
	const own = new AbortController()
	controller = own
	loading.value = true
	failure.value = null
	try {
		const res = await Api.talonUsage.getUsage(
			{ from: range.value[0], to: range.value[1], group_by: groupBy.value, customer_code: customer.value },
			own.signal
		)
		if (controller !== own) return
		report.value = res.data
	} catch (err) {
		if (controller !== own || own.signal.aborted) return
		report.value = null
		failure.value = talonFailure(err)
	} finally {
		if (controller === own) loading.value = false
	}
}

watch([() => range.value?.join(","), groupBy, customer], () => load(), { immediate: true })

// The global filter wins when it changes; an emptied selection means every customer the caller has.
onGlobalCustomerFilterChange(codes => {
	customer.value = codes[0] ?? null
})

loadCustomers()
onBeforeUnmount(() => controller?.abort())
</script>
