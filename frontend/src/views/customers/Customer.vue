<template>
	<div class="page flex flex-col gap-4">
		<div class="flex min-w-0 items-center gap-4">
			<n-button quaternary class="shrink-0" @click="goBack(routeCustomer())">
				<template #icon>
					<Icon :name="BackIcon" />
				</template>
				Back
			</n-button>

			<div v-if="customerCode" class="flex min-w-0 flex-wrap items-baseline gap-2">
				<span v-if="customer?.customer_name" class="truncate text-lg font-semibold">
					{{ customer.customer_name }}
				</span>
				<span class="text-secondary font-mono text-sm">#{{ customer?.customer_code ?? customerCode }}</span>
			</div>
		</div>

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
import { NButton, NEmpty } from "naive-ui"
import { ref, watch } from "vue"
import Icon from "@/components/common/Icon.vue"
import CustomerDetails from "@/components/customers/CustomerDetails.vue"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"

const { goBack, routeCustomer } = useNavigation()

const BackIcon = "carbon:arrow-left"
const customer = ref<Customer | null>(null)

const customerCode = useRouteParam("code")

watch(customerCode, () => {
	customer.value = null
})
</script>
