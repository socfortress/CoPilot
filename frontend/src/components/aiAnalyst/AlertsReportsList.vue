<template>
	<div class="alerts-reports-list @container">
		<div class="flex items-center justify-between gap-2">
			<div class="flex items-center gap-2">
				<div class="flex items-center gap-1 text-sm">
					<span>Total</span>
					<code class="py-1">{{ alertsList.length }}</code>
				</div>
			</div>

			<div class="flex items-center justify-end gap-2 whitespace-nowrap">
				<n-select
					v-model:value="customerFilter"
					size="small"
					clearable
					placeholder="All customers"
					:options="customerOptions"
					:show-checkmark="false"
					class="min-w-40"
					:disabled="loading"
				/>
				<n-select
					v-model:value="sort"
					size="small"
					:options="sortOptions"
					:show-checkmark="false"
					class="max-w-20"
					:disabled="loading"
				/>
			</div>
		</div>

		<n-spin :show="loading">
			<div class="my-3 flex min-h-52 flex-col gap-2">
				<template v-if="sortedList.length">
					<AlertReportItem
						v-for="alert of sortedList"
						:key="`${alert.alert_id}-${alert.report.id}`"
						:alert-data="alert"
						class="item-appear item-appear-bottom item-appear-005"
					/>
				</template>
				<template v-else>
					<n-empty
						v-if="!loading"
						description="No alerts with AI reports found"
						class="h-48 justify-center"
					/>
				</template>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { AlertWithReport } from "@/types/aiAnalyst.d"
import { NEmpty, NSelect, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"
import AlertReportItem from "./AlertReportItem.vue"

const message = useMessage()
const loading = ref(false)
const alertsList = ref<AlertWithReport[]>([])
const customerFilter = ref<string | null>(null)

const sort = ref<"desc" | "asc">("desc")
const sortOptions = [
	{ label: "Desc", value: "desc" },
	{ label: "Asc", value: "asc" }
]

const sortedList = computed(() => {
	const list = [...alertsList.value]
	return list.sort((a, b) => {
		const dateA = new Date(a.report.created_at).getTime()
		const dateB = new Date(b.report.created_at).getTime()
		return sort.value === "desc" ? dateB - dateA : dateA - dateB
	})
})

const customerOptions = computed(() => {
	const codes = new Set(alertsList.value.map(a => a.customer_code))
	return Array.from(codes)
		.sort()
		.map(code => ({ label: code, value: code }))
})

function getData() {
	loading.value = true

	Api.aiAnalyst
		.getAlertsWithReports(customerFilter.value || undefined)
		.then(res => {
			if (res.data.success) {
				alertsList.value = res.data?.alerts || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			alertsList.value = []
			message.error(getApiErrorMessage(err) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

// Refetch only on actual user-driven filter changes. Previously wired via
// @update:value on the select, but naive-ui can fire update:value when the
// options prop identity changes (our computed returns a new array each time
// alertsList updates) — that created a feedback loop: fetch → options ref
// changes → update:value fires → fetch again.
watch(customerFilter, () => {
	getData()
})

onBeforeMount(() => {
	getData()
})
</script>
