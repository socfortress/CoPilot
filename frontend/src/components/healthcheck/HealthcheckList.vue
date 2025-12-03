<template>
	<div class="healthcheck-list">
		<div ref="header" class="header flex items-center justify-end gap-2">
			<div class="info flex grow gap-2">
				<n-popover overlap placement="bottom-start">
					<template #trigger>
						<div class="bg-default rounded-lg">
							<n-button size="small" class="cursor-help!">
								<template #icon>
									<Icon :name="InfoIcon" />
								</template>
							</n-button>
						</div>
					</template>
					<div class="flex flex-col gap-2">
						<div class="box">
							Total :
							<code>{{ stats?.total_count || 0 }}</code>
						</div>
						<div class="box text-error-500">
							Active :
							<code>{{ stats?.active_alerts_count || 0 }}</code>
						</div>
						<div class="box text-warning-500">
							Critical :
							<code>{{ criticalTotal }}</code>
						</div>
						<div class="box text-success-500">
							Cleared :
							<code>{{ stats?.cleared_alerts_count || 0 }}</code>
						</div>
					</div>
				</n-popover>
			</div>
			<div class="flex items-center gap-2">
				<n-select
					v-model:value="checkNameFilter"
					:options="checkNameOptions"
					size="small"
					class="w-48!"
					placeholder="Filter by check name"
					clearable
					filterable
					@update:value="getData"
				/>
				<n-select
					v-model:value="statusFilter"
					:options="statusOptions"
					size="small"
					class="w-32!"
					@update:value="getData"
				/>
				<n-checkbox v-model:checked="excludeOk" size="small" @update:checked="getData">Exclude OK</n-checkbox>
			</div>
			<n-pagination
				v-model:page="currentPage"
				v-model:page-size="pageSize"
				:page-slot="pageSlot"
				:show-size-picker="showSizePicker"
				:page-sizes="pageSizes"
				:item-count="total"
				:simple="simpleMode"
			/>
		</div>
		<n-spin :show="loading">
			<div class="my-3 flex min-h-52 flex-col gap-2">
				<template v-if="healthcheckList.length">
					<HealthcheckItem
						v-for="alert of itemsPaginated"
						:key="(alert.check_id || '') + alert.time"
						:alert="alert"
						class="item-appear item-appear-bottom item-appear-005"
					/>
				</template>
				<template v-else>
					<n-empty v-if="!loading" description="No items found" class="h-48 justify-center" />
				</template>
			</div>
		</n-spin>
		<div class="footer flex justify-end">
			<n-pagination
				v-if="itemsPaginated.length > 3"
				v-model:page="currentPage"
				:page-size="pageSize"
				:item-count="total"
				:page-slot="6"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { InfluxDBAlert, InfluxDBAlertResponse } from "@/types/healthchecks.d"
import { useResizeObserver } from "@vueuse/core"
import _orderBy from "lodash/orderBy"
import { NButton, NCheckbox, NEmpty, NPagination, NPopover, NSelect, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { InfluxDBAlertSeverity } from "@/types/healthchecks.d"
import HealthcheckItem from "./HealthcheckItem.vue"

const message = useMessage()
const loading = ref(false)
const healthcheckList = ref<InfluxDBAlert[]>([])
const stats = ref<InfluxDBAlertResponse | null>(null)
const checkNames = ref<string[]>([])

const pageSize = ref(25)
const currentPage = ref(1)
const simpleMode = ref(false)
const showSizePicker = ref(true)
const pageSizes = [10, 25, 50, 100]
const header = ref()
const pageSlot = ref(8)

// Filters
const statusFilter = ref<"all" | "active" | "cleared">("all")
const excludeOk = ref(false)
const checkNameFilter = ref<string | null>(null)

const statusOptions = [
	{ label: "All", value: "all" },
	{ label: "Active", value: "active" },
	{ label: "Cleared", value: "cleared" }
]

const checkNameOptions = computed(() => [
	{ label: "All Checks" },
	...checkNames.value.map(name => ({ label: name, value: name }))
])

const itemsPaginated = computed(() => {
	const from = (currentPage.value - 1) * pageSize.value
	const to = currentPage.value * pageSize.value

	const list = _orderBy(
		healthcheckList.value,
		[
			// Sort by severity priority
			item => {
				const severityOrder = {
					[InfluxDBAlertSeverity.Critical]: 0,
					[InfluxDBAlertSeverity.Warning]: 1,
					[InfluxDBAlertSeverity.Info]: 2,
					[InfluxDBAlertSeverity.Ok]: 3
				}
				return severityOrder[item.severity as InfluxDBAlertSeverity]
			},
			"time"
		],
		["asc", "desc"]
	)

	return list.slice(from, to)
})

const InfoIcon = "carbon:information"

const total = computed<number>(() => {
	return healthcheckList.value.length || 0
})

const criticalTotal = computed<number>(() => {
	return healthcheckList.value.filter(o => o.severity === InfluxDBAlertSeverity.Critical).length || 0
})

function getCheckNames() {
	Api.healthchecks
		.getCheckNames()
		.then(res => {
			if (res.data.success) {
				checkNames.value = res.data.check_names || []
			}
		})
		.catch(() => {
			checkNames.value = []
		})
}

function getData() {
	loading.value = true

	Api.healthchecks
		.getHealthchecks({
			days: 7,
			status: statusFilter.value,
			exclude_ok: excludeOk.value,
			check_name: checkNameFilter.value || undefined
		})
		.then(res => {
			if (res.data.success) {
				healthcheckList.value = res.data.alerts || []
				stats.value = res.data
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			healthcheckList.value = []
			stats.value = null

			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

useResizeObserver(header, entries => {
	const entry = entries[0]
	const { width } = entry.contentRect

	pageSlot.value = width < 650 ? 5 : 8
	simpleMode.value = width < 450
})

onBeforeMount(() => {
	getCheckNames()
	getData()
})
</script>
