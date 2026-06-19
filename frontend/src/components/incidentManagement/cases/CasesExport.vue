<template>
	<div>
		<n-button :size :loading="exporting" secondary @click="openModal">
			<template v-if="showIcon" #icon>
				<Icon :name="DownloadIcon" :size="14" />
			</template>
			Export
		</n-button>

		<n-modal
			v-model:show="showModal"
			display-directive="show"
			preset="card"
			:style="{ maxWidth: 'min(480px, 90vw)' }"
			title="Export Cases"
			:bordered="false"
			content-class="flex flex-col"
			segmented
		>
			<n-form label-placement="top">
				<n-form-item label="Period">
					<n-date-picker
						v-model:value="form.period"
						type="month"
						clearable
						placeholder="All time"
						class="w-full"
						:is-date-disabled="isMonthDisabled"
					/>
				</n-form-item>

				<n-form-item label="Customers">
					<n-select
						v-model:value="form.customerCodes"
						:options="customerOptions"
						multiple
						filterable
						clearable
						placeholder="All customers"
						:loading="loadingCustomersList"
					/>
				</n-form-item>
			</n-form>

			<div class="mt-4 flex justify-end gap-3">
				<n-button @click="showModal = false">Cancel</n-button>
				<n-button type="primary" :loading="exporting" @click="handleExport">Export</n-button>
			</div>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { ButtonSize } from "naive-ui"
import type { Ref } from "vue"
import type { ApiError } from "@/types/common"
import type { Customer } from "@/types/customers"
import { saveAs } from "file-saver"
import { NButton, NDatePicker, NForm, NFormItem, NModal, NSelect, useMessage } from "naive-ui"
import { computed, inject, reactive, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"

const { size, showIcon } = defineProps<{ size?: ButtonSize; showIcon?: boolean }>()

const DownloadIcon = "carbon:cloud-download"
const loadingCustomersList = ref(false)
const dFormats = useSettingsStore().dateFormat
const exporting = ref(false)
const showModal = ref(false)
const message = useMessage()
const customersList = inject<Ref<Customer[]>>("customers-list", ref([]))

const form = reactive({
	period: null as number | null,
	customerCodes: [] as string[]
})

const customerOptions = computed(() =>
	customersList.value.map(customer => ({
		label: `#${customer.customer_code} - ${customer.customer_name}`,
		value: customer.customer_code
	}))
)

function isMonthDisabled(ts: number) {
	const date = new Date(ts)
	const now = new Date()

	return (
		date.getFullYear() > now.getFullYear() ||
		(date.getFullYear() === now.getFullYear() && date.getMonth() > now.getMonth())
	)
}

function openModal() {
	load()
	showModal.value = true
}

function parsePeriod(period: number | null) {
	if (!period) {
		return { year: undefined, month: undefined }
	}

	const date = new Date(period)
	return {
		year: date.getFullYear(),
		month: date.getMonth() + 1
	}
}

async function exportCasesFile(customerCode: string | undefined, fileName: string) {
	const { year, month } = parsePeriod(form.period)

	const res = await Api.incidentManagement.cases.exportCases({
		customerCode,
		year,
		month
	})

	if (res.data) {
		saveAs(new Blob([res.data], { type: "text/csv;charset=utf-8" }), fileName)
		return
	}

	throw new Error("An error occurred. Please try again later.")
}

async function handleExport() {
	exporting.value = true

	const { year, month } = parsePeriod(form.period)
	const monthSuffix = year && month ? `_${year}-${String(month).padStart(2, "0")}` : ""
	const timestamp = formatDate(new Date(), dFormats.datetimesec)

	try {
		if (!form.customerCodes.length) {
			await exportCasesFile(undefined, `cases${monthSuffix}_${timestamp}.csv`)
		} else {
			for (const customerCode of form.customerCodes) {
				await exportCasesFile(customerCode, `cases_customer:${customerCode}${monthSuffix}_${timestamp}.csv`)
			}
		}

		showModal.value = false
		form.period = null
		form.customerCodes = []
	} catch (err) {
		message.error(
			getApiErrorMessage(err as ApiError) ||
				(err as Error).message ||
				"An error occurred. Please try again later."
		)
	} finally {
		exporting.value = false
	}
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
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
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
