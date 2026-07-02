<template>
	<div class="sidebar-footer bg-body flex flex-col gap-4 rounded-lg p-2" :class="{ 'collapsed gap-2!': collapsed }">
		<div v-if="collapsed" class="flex flex-col items-center gap-2 py-1">
			<n-badge
				:value="selected?.length || 0"
				class="[&_.n-badge-sup]:text-2xs! [&_.n-badge-sup]:bg-default! [&_.n-badge-sup]:border-default! [&_.n-badge-sup]:border!"
			>
				<Icon name="carbon:edit-filter" :size="18" class="text-secondary" />
			</n-badge>
		</div>
		<div v-else class="flex flex-col gap-1">
			<div class="text-secondary text-2xs truncate px-px uppercase">Global customers filter</div>
			<n-select
				v-model:value="selected"
				multiple
				to=".sidebar-footer"
				clearable
				size="small"
				class="w-full"
				:options
				:max-tag-count="collapsed ? 0 : 2"
				:placeholder="collapsed ? '…' : 'All customers'"
				:consistent-menu-width="false"
				:loading
			/>
		</div>

		<SidebarContextPanel :collapsed />
	</div>
</template>

<script lang="ts" setup>
import type { ApiError } from "@/types/common"
import type { Customer } from "@/types/customers"
import { NBadge, NSelect } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import SidebarContextPanel from "@/app-layouts/VerticalNav/SidebarContextPanel.vue"
import Icon from "@/components/common/Icon.vue"
import { useCustomerFilterStore } from "@/stores/customer-filter"
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
