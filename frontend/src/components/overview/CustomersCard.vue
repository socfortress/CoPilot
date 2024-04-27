<template>
	<n-spin :show="loading">
		<CardStats
			title="Customers"
			:value="total"
			:vertical="vertical"
			hovered
			class="cursor-pointer h-full"
			@click="gotoCustomer()"
		>
			<template #icon>
				<CardStatsIcon :iconName="CustomersIcon" boxed :boxSize="40"></CardStatsIcon>
			</template>
		</CardStats>
	</n-spin>
</template>

<script setup lang="ts">
import { computed, onBeforeMount, ref, toRefs } from "vue"
import CardStatsIcon from "@/components/common/CardStatsIcon.vue"
import CardStats from "@/components/common/CardStats.vue"
import Api from "@/api"
import { useMessage, NSpin } from "naive-ui"
import type { Customer } from "@/types/customers.d"
import { useGoto } from "@/composables/useGoto"

const props = defineProps<{
	vertical?: boolean
}>()
const { vertical } = toRefs(props)

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
