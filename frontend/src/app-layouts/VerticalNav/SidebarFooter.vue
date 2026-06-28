<template>
	<div class="sidebar-footer bg-body rounded-lg p-2" :class="{ collapsed }">
		<n-select
			v-if="options.length > 1"
			v-model:value="selected"
			multiple
			clearable
			size="small"
			class="w-full"
			:options
			:max-tag-count="collapsed ? 0 : 2"
			:placeholder="collapsed ? '…' : 'All customers'"
			:consistent-menu-width="false"
			:loading
		/>
		<p v-else-if="options.length === 1" class="text-secondary truncate px-1 font-mono text-xs">
			{{ options[0].label }}
		</p>
	</div>
</template>

<script lang="ts" setup>
import type { ApiError } from "@/types/common"
import type { Customer } from "@/types/customers"
import { NSelect } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import { useCustomerFilterStore } from "@/stores/customerFilter"
import { getApiErrorMessage } from "@/utils"

const { collapsed = false } = defineProps<{
	collapsed?: boolean
}>()

const customerFilterStore = useCustomerFilterStore()
const customersList = ref<Customer[]>([])
const loading = ref(false)

const options = computed(() =>
	customersList.value.map(c => ({
		label: c.customer_name ? `#${c.customer_code} - ${c.customer_name}` : c.customer_code,
		value: c.customer_code
	}))
)

const selected = computed<string[]>({
	get: () => customerFilterStore.selectedCustomerCodes,
	set: (codes: string[]) => customerFilterStore.setSelected(codes)
})

function loadCustomers() {
	loading.value = true
	Api.customers
		.getCustomers()
		.then(res => {
			if (res.data.success) {
				customersList.value = res.data.customers || []
				customerFilterStore.pruneToAccessible(customersList.value.map(c => c.customer_code))
			}
		})
		.catch(err => {
			console.warn(getApiErrorMessage(err as ApiError) || "Failed to load customers for sidebar filter")
		})
		.finally(() => {
			loading.value = false
		})
}

onBeforeMount(() => {
	loadCustomers()
})
</script>
