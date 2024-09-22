<template>
	<n-dropdown placement="bottom-start" trigger="click" :options="customersOptions" @select="exportCases">
		<n-button :size :loading="exporting" secondary @click="load()">
			<template #icon>
				<Icon :name="DownloadIcon" :size="14" />
			</template>
			Export
		</n-button>
	</n-dropdown>
</template>

<script setup lang="ts">
import type { Customer } from "@/types/customers.d"
import type { Size } from "naive-ui/es/button/src/interface"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import { saveAs } from "file-saver"
import { NButton, NDropdown, useMessage } from "naive-ui"
import { computed, inject, ref, type Ref } from "vue"

const { size } = defineProps<{ size?: Size }>()

const DownloadIcon = "carbon:cloud-download"
const loadingCustomersList = ref(false)
const dFormats = useSettingsStore().dateFormat
const exporting = ref(false)
const message = useMessage()
const customersList = inject<Ref<Customer[]>>("customers-list", ref([]))

const customersOptions = computed(() => {
	return [
		{
			label: "Export All Cases",
			key: "--all--"
		},
		{
			label: `Export by Customer${loadingCustomersList.value ? "..." : ""}`,
			key: "customer",
			disabled: loadingCustomersList.value,
			children: loadingCustomersList.value
				? undefined
				: customersList.value.map(o => ({
						label: `#${o.customer_code} - ${o.customer_name}`,
						key: o.customer_code
				  }))
		}
	]
})

function exportCases(key: string) {
	exporting.value = true

	const fileName =
		key === "--all--"
			? `cases_${formatDate(new Date(), dFormats.datetimesec)}.csv`
			: `cases_customer:${key}_${formatDate(new Date(), dFormats.datetimesec)}.csv`

	Api.incidentManagement
		.exportCases(key === "--all--" ? undefined : key)
		.then(res => {
			if (res.data) {
				saveAs(new Blob([res.data], { type: "text/csv;charset=utf-8" }), fileName)
			} else {
				message.warning("An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			exporting.value = false
		})
}

function getCustomers() {
	loadingCustomersList.value = true

	Api.customers
		.getCustomers()
		.then(res => {
			if (res.data.success) {
				customersList.value = res.data?.customers || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingCustomersList.value = false
		})
}

function load() {
	if (!customersList.value.length) {
		getCustomers()
	}
}
</script>
