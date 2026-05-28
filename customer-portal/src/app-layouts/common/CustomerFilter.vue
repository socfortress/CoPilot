<template>
	<NSelect
		v-if="options.length > 1"
		v-model:value="selected"
		multiple
		clearable
		size="small"
		class="customer-filter"
		:options
		:max-tag-count="2"
		placeholder="All customers"
		:consistent-menu-width="false"
	/>
</template>

<script lang="ts" setup>
import { NSelect } from "naive-ui"
import { computed, onMounted } from "vue"
import { useAuthStore } from "@/stores/auth"
import { useCustomerFilterStore } from "@/stores/customerFilter"

const authStore = useAuthStore()
const customerFilterStore = useCustomerFilterStore()

const options = computed(() => authStore.accessibleCustomerCodes.map(code => ({ label: code, value: code })))

const selected = computed<string[]>({
	get: () => customerFilterStore.selectedCustomerCodes,
	set: (codes: string[]) => customerFilterStore.setSelected(codes)
})

// Drop any persisted selection the current user can no longer access.
onMounted(() => {
	customerFilterStore.pruneToAccessible(authStore.accessibleCustomerCodes)
})
</script>

<style lang="scss" scoped>
.customer-filter {
	min-width: 200px;
	max-width: 280px;
}
</style>
