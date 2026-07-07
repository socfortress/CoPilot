<template>
	<n-spin :show="loading">
		<CustomerDetailsTabs
			v-if="tabCustomer"
			:customer="tabCustomer"
			:customer-info
			:customer-meta
			:customer-portainer-stack-id
			:use-max-height
			v-model:loading-delete="loadingDelete"
			@delete="emit('delete')"
			@update:customer-info="customerInfo = $event"
			@update:customer-meta="customerMeta = $event"
		/>
	</n-spin>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { Customer, CustomerMeta } from "@/types/customers"
import { NSpin, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"
import CustomerDetailsTabs from "./CustomerDetailsTabs.vue"

const props = defineProps<{
	customer?: Customer | null
	customerCode?: string | null
	useMaxHeight?: boolean
}>()

const emit = defineEmits<{
	(e: "delete"): void
	(e: "loaded", value: Customer): void
}>()

const message = useMessage()
const loading = ref(false)
const loadingDelete = ref(false)
const customerInfo = ref<Customer | null>(null)
const customerMeta = ref<CustomerMeta | null>(null)
const customerPortainerStackId = ref<number | null>(null)

const resolvedCode = computed(() => props.customer?.customer_code ?? props.customerCode ?? null)

const tabCustomer = computed<Customer | null>(() => {
	if (customerInfo.value) return customerInfo.value
	if (props.customer) return props.customer
	if (resolvedCode.value) {
		return {
			customer_code: resolvedCode.value,
			customer_name: "",
			contact_last_name: "",
			contact_first_name: "",
			parent_customer_code: null,
			phone: "",
			address_line1: "",
			address_line2: "",
			city: "",
			state: "",
			postal_code: "",
			country: "",
			customer_type: "",
			logo_file: ""
		}
	}
	return null
})

function getFull() {
	const code = resolvedCode.value
	if (!code) return

	loading.value = true

	Api.customers
		.getCustomerFull(code)
		.then(res => {
			if (res.data.success) {
				customerInfo.value = res.data.customer
				customerMeta.value = res.data.customer_meta || null
				emit("loaded", res.data.customer)
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

function getPortainerStackId() {
	const name = customerInfo.value?.customer_name || props.customer?.customer_name
	if (!name) return

	Api.portainer.getCustomerStackId(name).then(res => {
		if (res.data.success) {
			customerPortainerStackId.value = res.data.stack_id || null
		} else {
			message.warning(res.data?.message || "An error occurred. Please try again later.")
		}
	})
}

function ensureLoaded() {
	if (!resolvedCode.value) return

	if (props.customer?.customer_name) {
		customerInfo.value = props.customer
	}

	if (
		!customerInfo.value?.customer_name ||
		!customerMeta.value?.customer_meta_graylog_index
	) {
		getFull()
	}

	if (customerPortainerStackId.value === null) {
		getPortainerStackId()
	}
}

watch(
	() => [props.customer, props.customerCode] as const,
	([customer, customerCode]) => {
		customerInfo.value = customer?.customer_name ? customer : null
		customerMeta.value = null
		customerPortainerStackId.value = null

		if (customer || customerCode) {
			ensureLoaded()
		}
	},
	{ immediate: true }
)

watch(customerInfo, info => {
	if (info?.customer_name && customerPortainerStackId.value === null) {
		getPortainerStackId()
	}
})

defineExpose({ loading, customerInfo, customerMeta })
</script>
