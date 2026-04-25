<template>
	<div class="flex flex-wrap items-center justify-between gap-3">
		<div class="flex items-center gap-2 text-sm">
			<span>Customer</span>
			<n-select
				v-model:value="customer"
				size="small"
				placeholder="Select a customer"
				:options="customerOptions"
				:show-checkmark="false"
				class="min-w-52"
				:loading="customerBootstrapLoading"
			/>
		</div>
		<div class="flex items-center gap-2">
			<n-button size="small" :disabled="!customer" @click="showConsolidation = true">
				<template #icon>
					<Icon :name="ConsolidateIcon" />
				</template>
				Consolidate lessons
			</n-button>
			<n-button size="small" :disabled="!customer" :loading @click="refresh()">
				<template #icon>
					<Icon :name="RefreshIcon" />
				</template>
				Refresh
			</n-button>
		</div>

		<PalaceConsolidationDrawer v-if="customer" v-model:show="showConsolidation" :customer-code="customer" />
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import { NButton, NSelect, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"
import PalaceConsolidationDrawer from "./PalaceConsolidationDrawer.vue"

const emit = defineEmits<{
	(e: "refresh"): void
}>()
const RefreshIcon = "carbon:renew"
const ConsolidateIcon = "carbon:data-collection"

const message = useMessage()

const loading = defineModel<boolean>("loading")

const customer = defineModel<string | null>("customer")
const customerOptions = ref<{ label: string; value: string }[]>([])
const customerBootstrapLoading = ref(false)

const showConsolidation = ref(false)

async function bootstrapCustomers() {
	// Bootstrap customer picker off alerts_with_reports so we only list
	// customers that actually have AI runs — no external customer endpoint call.
	customerBootstrapLoading.value = true

	try {
		const res = await Api.aiAnalyst.getAlertsWithReports()
		if (res.data.success) {
			const codes = new Set((res.data.alerts || []).map(a => a.customer_code))
			customerOptions.value = Array.from(codes)
				.sort()
				.map(c => ({ label: c, value: c }))
			if (customerOptions.value.length && !customer.value) {
				// The watch(customer, loadStats) below picks this up — no
				// need to call loadStats() explicitly from bootstrap.
				customer.value = customerOptions.value[0].value
			}
		}
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Failed to load customers")
	} finally {
		customerBootstrapLoading.value = false
	}
}

function refresh() {
	emit("refresh")
}

onBeforeMount(() => {
	bootstrapCustomers()
})
</script>
