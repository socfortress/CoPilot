<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader :back-route="routeCustomer()" />

		<div class="w-full">
			<CustomerForm @submitted="onSubmitted" />
		</div>
	</div>
</template>

<script setup lang="ts">
import type { Customer } from "@/types/customers"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import CustomerForm from "@/components/customers/CustomerForm.vue"
import { useNavigation } from "@/composables/useNavigation"

const { routeCustomer } = useNavigation()

function onSubmitted(customer: Customer) {
	routeCustomer({ code: customer.customer_code }).navigate()
}
</script>
