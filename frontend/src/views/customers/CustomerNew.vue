<template>
	<div class="page flex flex-col gap-4">
		<n-button quaternary class="self-start" @click="routeCustomer().navigate()">
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
import Icon from "@/components/common/Icon.vue"
import CustomerForm from "@/components/customers/CustomerForm.vue"
import { useNavigation } from "@/composables/useNavigation"

const BackIcon = "carbon:arrow-left"
const { routeCustomer } = useNavigation()

function onSubmitted(customer: Customer) {
	routeCustomer({ code: customer.customer_code }).navigate()
}
</script>
