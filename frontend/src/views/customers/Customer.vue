<template>
	<div class="page flex flex-col gap-4">
		<div class="flex min-w-0 items-center gap-4">
			<n-button quaternary class="shrink-0" @click="goBack">
				<template #icon>
					<Icon :name="BackIcon" />
				</template>
				Back
			</n-button>

			<div v-if="customerCode" class="flex min-w-0 flex-wrap items-baseline gap-2">
				<span v-if="customer?.customer_name" class="truncate text-lg font-semibold">
					{{ customer.customer_name }}
				</span>
				<span class="font-mono text-sm text-secondary">#{{ customer?.customer_code ?? customerCode }}</span>
			</div>
		</div>

		<CustomerDetails
			v-if="customerCode"
			:customer-code
			@delete="router.push({ name: 'Customers' })"
			@loaded="customer = $event"
		/>
		<n-empty v-else description="Invalid customer code" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import type { Customer } from "@/types/customers"
import { NButton, NEmpty } from "naive-ui"
import { computed, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import Icon from "@/components/common/Icon.vue"
import CustomerDetails from "@/components/customers/CustomerDetails.vue"

const route = useRoute()
const router = useRouter()

const BackIcon = "carbon:arrow-left"
const customer = ref<Customer | null>(null)

const customerCode = computed(() => {
	const raw = route.params.code
	if (!raw) return null
	return Array.isArray(raw) ? raw[0] : String(raw)
})

watch(customerCode, () => {
	customer.value = null
})

function goBack() {
	if (window.history.length > 1) {
		router.back()
		return
	}

	router.push({ name: "Customers" })
}
</script>
