<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader :title="customer?.customer_name || undefined" :back-route="routeCustomer()">
			<template v-if="customerCode" #meta>
				<span class="text-secondary font-mono text-sm">#{{ customer?.customer_code ?? customerCode }}</span>
			</template>
		</DetailPageHeader>

		<CustomerDetails
			v-if="customerCode"
			:customer-code
			@delete="routeCustomer().navigate()"
			@loaded="customer = $event"
		/>
		<n-empty v-else description="Invalid customer code" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import type { Customer } from "@/types/customers"
import { NEmpty } from "naive-ui"
import { ref, watch } from "vue"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import CustomerDetails from "@/components/customers/CustomerDetails.vue"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"

const { routeCustomer } = useNavigation()

const customer = ref<Customer | null>(null)

const customerCode = useRouteParam("code")

watch(customerCode, () => {
	customer.value = null
})
</script>
