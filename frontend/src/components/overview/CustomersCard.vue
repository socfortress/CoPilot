<template>
	<n-spin :show="loading">
		<CardStatsMulti
			title="Customers"
			hovered
			class="cursor-pointer h-full"
			:values="[{ value: total, label: 'Total' }]"
			@click="gotoCustomer()"
		>
			<template #icon>
				<CardStatsIcon :icon-name="CustomersIcon" boxed :box-size="30"></CardStatsIcon>
			</template>
		</CardStatsMulti>
	</n-spin>
</template>

<script setup lang="ts">
import type { Customer } from "@/types/customers.d"
import Api from "@/api"
import CardStatsIcon from "@/components/common/CardStatsIcon.vue"
import CardStatsMulti from "@/components/common/CardStatsMulti.vue"
import { useGoto } from "@/composables/useGoto"
import { NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"

const CustomersIcon = "carbon:user-multiple"
const { gotoCustomer } = useGoto()
const message = useMessage()
const loading = ref(false)
const customers = ref<Customer[]>([])

const total = computed<number>(() => {
	return customers.value.length || 0
})

function getData() {
	loading.value = true

	Api.customers
		.getCustomers()
		.then(res => {
			if (res.data.success) {
				customers.value = res.data?.customers || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(() => {
	getData()
})
</script>

<style lang="scss" scoped>
.n-spin-container {
	:deep() {
		.n-spin-content {
			height: 100%;
		}
	}
}
</style>
