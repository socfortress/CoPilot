<template>
	<n-select
		v-model:value="codes"
		:options
		:loading
		multiple
		to="body"
		filterable
		placeholder="Choose customers"
		data-testid="user-customers-select"
	/>
</template>

<script setup lang="ts">
// The customers a user works on, picked by name or code. Used wherever an analyst or
// responder gets customers: creating the user, changing their role, assigning them.
import type { Customer } from "@/types/customers"
import { NSelect, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"

const codes = defineModel<string[]>("value", { default: () => [] })

const message = useMessage()
const loading = ref(false)
const customers = ref<Customer[]>([])

const options = computed(() =>
	customers.value.map(customer => ({
		label: `${customer.customer_name} (${customer.customer_code})`,
		value: customer.customer_code
	}))
)

async function load() {
	loading.value = true
	try {
		const res = await Api.customers.getCustomers({})
		if (res.data.success && res.data.customers) customers.value = res.data.customers
	} catch {
		message.error("Failed to load customers")
	} finally {
		loading.value = false
	}
}

onBeforeMount(load)
</script>
