<template>
	<n-dropdown placement="bottom-start" trigger="click" :options="customersOptions" @select="exportCases">
		<n-button :size :loading="exporting" secondary @click="load()">
			<template v-if="showIcon" #icon>
				<Icon :name="DownloadIcon" :size="14" />
			</template>
			Export
		</n-button>
	</n-dropdown>
</template>

<script setup lang="ts">
import type { Size } from "naive-ui/es/button/src/interface"
import type { DropdownMixedOption } from "naive-ui/es/dropdown/src/interface"
import type { Ref } from "vue"
import type { Customer } from "@/types/customers.d"
import { useWindowSize } from "@vueuse/core"
import { saveAs } from "file-saver"
import { NButton, NDropdown, useMessage } from "naive-ui"
import { computed, h, inject, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"

const { size, showIcon } = defineProps<{ size?: Size; showIcon?: boolean }>()

const DownloadIcon = "carbon:cloud-download"
const loadingCustomersList = ref(false)
const dFormats = useSettingsStore().dateFormat
const exporting = ref(false)
const message = useMessage()
const { width: winWidth } = useWindowSize()
const customersList = inject<Ref<Customer[]>>("customers-list", ref([]))

const customersOptions = computed(() => {
	const options: DropdownMixedOption[] = [
		{
			label: "Export All Cases",
			key: "--all--"
		}
	]

	if (winWidth.value > 550) {
		options.push({
			label: `Export by Customer${loadingCustomersList.value ? "..." : ""}`,
			key: "customer",
			disabled: loadingCustomersList.value,
			children: loadingCustomersList.value
				? undefined
				: [
						{
							label: () => h("div", { class: "pl-2" }, "Select a Customer"),
							type: "group",
							children: customersList.value.map(o => ({
								label: `#${o.customer_code} - ${o.customer_name}`,
								key: o.customer_code
							}))
						}
					]
		})
	} else {
		options.push({
			label: () => h("div", { class: "pl-2" }, "Select a Customer"),
			type: "group",
			children: customersList.value.map(o => ({
				label: `#${o.customer_code} - ${o.customer_name}`,
				key: o.customer_code
			}))
		})
	}

	return options
})

function exportCases(key: string) {
	exporting.value = true

	const fileName =
		key === "--all--"
			? `cases_${formatDate(new Date(), dFormats.datetimesec)}.csv`
			: `cases_customer:${key}_${formatDate(new Date(), dFormats.datetimesec)}.csv`

	Api.incidentManagement.cases
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
