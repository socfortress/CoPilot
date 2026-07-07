<template>
	<div class="page flex flex-col gap-4">
		<n-button quaternary class="self-start" @click="router.push({ name: 'Customers' })">
			<template #icon>
				<Icon :name="BackIcon" />
			</template>
			Back to customers
		</n-button>

		<div class="w-full">
			<CustomerForm @submitted="onSubmitted" />
		</div>
	</div>
</template>

<script setup lang="ts">
import type { Customer } from "@/types/customers"
import { NButton } from "naive-ui"
import { useRouter } from "vue-router"
import CustomerForm from "@/components/customers/CustomerForm.vue"
import Icon from "@/components/common/Icon.vue"

const BackIcon = "carbon:arrow-left"
const router = useRouter()

function onSubmitted(customer: Customer) {
	router.push({ name: "Customer", params: { code: customer.customer_code } })
}
</script>
