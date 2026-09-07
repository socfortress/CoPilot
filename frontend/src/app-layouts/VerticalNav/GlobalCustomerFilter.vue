<template>
	<div v-if="collapsed" class="flex flex-col items-center gap-2 py-1">
		<n-badge
			:value="selected?.length || 0"
			class="[&_.n-badge-sup]:text-2xs! [&_.n-badge-sup]:bg-default! [&_.n-badge-sup]:border-default! [&_.n-badge-sup]:border!"
		>
			<Icon name="carbon:edit-filter" :size="18" class="text-secondary" />
		</n-badge>
	</div>
	<div v-else class="flex flex-col gap-1">
		<div class="flex items-center gap-1 px-px">
			<span class="text-secondary text-2xs truncate uppercase">Global customers filter</span>
			<n-tooltip v-if="showUnassignedHint" trigger="hover" :style="{ maxWidth: '260px' }">
				<template #trigger>
					<Icon
						name="carbon:warning-alt"
						:size="12"
						class="text-warning shrink-0"
						data-testid="global-filter-unassigned-warning"
					/>
				</template>
				This filter narrows the view only. No customer is assigned to your account, so you can still
				reach every customer in the deployment — ask an admin to assign yours under Users → Assign
				Customer.
			</n-tooltip>
		</div>
		<n-select
			v-model:value="selected"
			data-testid="global-customer-filter"
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
</template>

<script lang="ts" setup>
import type { ApiError } from "@/types/common"
import type { Customer } from "@/types/customers"
import { NBadge, NSelect, NTooltip } from "naive-ui"
import { computed, onBeforeUnmount, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useAuthStore } from "@/stores/auth"
import { useCustomerFilterStore } from "@/stores/customer-filter"
import { getApiErrorMessage } from "@/utils"

const { collapsed = false } = defineProps<{
	collapsed?: boolean
}>()

const authStore = useAuthStore()
const customerFilterStore = useCustomerFilterStore()
const customersList = ref<Customer[]>([])
const loading = ref(false)
// An analyst with no `user_customer_access` rows keeps deployment-wide access (#1050
// kept that so upgrading does not strip every existing analyst). Picking a customer
// here then looks like an assignment while it is only a view filter — which is exactly
// how "I assigned a customer and the analyst still sees the others" gets reported.
const accessScope = ref<"assigned" | "deployment" | "unassigned" | null>(null)
const showUnassignedHint = computed(() => accessScope.value === "unassigned")
const isLogged = computed(() => authStore.isLogged)

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

// This filter lives in the layout, not in a page: it is mounted once and stays
// for the whole session. Owning a controller keeps it out of the router's
// navigation scope (#1072) — otherwise navigating while it loads would abort it
// and leave the sidebar filter permanently empty, since nothing retries it.
let abortController: AbortController | null = null

function loadCustomers() {
	abortController?.abort()
	abortController = new AbortController()

	loading.value = true

	Api.auth
		.getMyCustomerAccess(abortController.signal)
		.then(res => {
			accessScope.value = res.data.scope ?? null
		})
		.catch(() => {
			// purely informational — never block the filter on it
			accessScope.value = null
		})

	Api.customers
		.getCustomers({}, abortController.signal)
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

watch(
	isLogged,
	value => {
		if (value) {
			loadCustomers()
		}
	},
	{ immediate: true }
)

onBeforeUnmount(() => {
	abortController?.abort()
})
</script>
