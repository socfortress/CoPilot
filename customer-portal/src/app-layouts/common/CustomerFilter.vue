<template>
	<NSelect
		v-if="customerOptions.length > 1"
		v-model:value="selected"
		multiple
		clearable
		size="small"
		class="customer-filter"
		data-testid="customer-filter"
		:options="customerOptions"
		:render-label="renderCustomerLabel"
		:filter="filterCustomer"
		filterable
		:max-tag-count="2"
		placeholder="All customers"
		:consistent-menu-width="false"
	/>
</template>

<script lang="ts" setup>
import { NSelect } from "naive-ui"
import { computed, watch } from "vue"
import { useCustomers } from "@/composables/common/useCustomers"
import { useAuthStore } from "@/stores/auth"
import { useCustomerFilterStore } from "@/stores/customerFilter"

const authStore = useAuthStore()
const customerFilterStore = useCustomerFilterStore()
const { customerOptions, filterCustomer, renderCustomerLabel } = useCustomers()

const selected = computed<string[]>({
	get: () => customerFilterStore.selectedCustomerCodes,
	set: (codes: string[]) => customerFilterStore.setSelected(codes)
})

// Drop any persisted selection the current user can no longer access — again whenever
// the list changes, since the live one (GET /customer_portal/me) arrives after the token's.
watch(
	() => authStore.accessibleCustomerCodes,
	codes => customerFilterStore.pruneToAccessible(codes),
	{ immediate: true }
)
</script>

<style lang="scss" scoped>
.customer-filter {
	min-width: 200px;
	max-width: 280px;
}
</style>
