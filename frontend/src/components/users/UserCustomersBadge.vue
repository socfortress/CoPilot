<template>
	<!-- An admin sees every customer, whatever is assigned: a count would read as "none". -->
	<n-tag v-if="seesEveryCustomer(roleName)" size="small" :bordered="false" data-testid="user-customers-all">
		All customers
	</n-tag>

	<n-popover v-else-if="codes.length" trigger="hover" placement="bottom-start" :delay="150" class="p-0!">
		<template #trigger>
			<n-tag type="info" size="small" :bordered="false" class="cursor-help!" data-testid="user-customers-count">
				<template #icon>
					<Icon :name="CustomersIcon" :size="13" />
				</template>
				{{ codes.length }}
			</n-tag>
		</template>

		<div class="flex max-h-80 w-80 flex-col" data-testid="user-customers-list">
			<div class="border-default text-secondary border-b px-3 py-2 text-xs">
				{{ codes.length }} {{ codes.length === 1 ? "customer" : "customers" }}
			</div>
			<n-scrollbar class="max-h-68">
				<ul class="flex flex-col p-1.5">
					<li
						v-for="code of codes"
						:key="code"
						class="hover:bg-primary/5 flex items-center justify-between gap-3 rounded-md px-1.5 py-1.5"
						:data-testid="`user-customer-${code}`"
					>
						<div class="flex min-w-0 flex-col">
							<span class="text-default truncate text-sm" :title="nameOf(code)">{{ nameOf(code) }}</span>
							<span class="text-tertiary font-mono text-xs">#{{ code }}</span>
						</div>
						<EntityDetailsButton size="tiny" :route="routeCustomer({ code })" @view="openCustomer(code)" />
					</li>
				</ul>
			</n-scrollbar>
		</div>
	</n-popover>

	<CustomerDetailsModal
		v-model:show="showDetails"
		:customer-code="selectedCode"
		:title="selectedCode ? nameOf(selectedCode) : ''"
		@deleted="emit('customerDeleted')"
	/>
</template>

<script setup lang="ts">
import { NPopover, NScrollbar, NTag } from "naive-ui"
import { computed, ref } from "vue"
import EntityDetailsButton from "@/components/common/EntityDetailsButton.vue"
import Icon from "@/components/common/Icon.vue"
import CustomerDetailsModal from "@/components/customers/CustomerDetailsModal.vue"
import { useNavigation } from "@/composables/useNavigation"
import { seesEveryCustomer } from "./roles"

/**
 * The customers a user is assigned to, as a count; hovering it lists them, each with
 * the usual "View" (modal) and "Open" (page) actions.
 */
const props = defineProps<{
	customerCodes: string[]
	roleName?: string | null
	/** Customer names by code, loaded once by the list; the code stands in for a missing one. */
	customerNames?: Record<string, string>
}>()

const emit = defineEmits<{
	/** A customer was deleted from the modal: the list's assignments are stale. */
	(e: "customerDeleted"): void
}>()

const CustomersIcon = "carbon:enterprise"

const { routeCustomer } = useNavigation()
const showDetails = ref(false)
const selectedCode = ref<string | null>(null)

const codes = computed(() => [...props.customerCodes].sort((a, b) => nameOf(a).localeCompare(nameOf(b))))

function nameOf(code: string) {
	return props.customerNames?.[code] || code
}

function openCustomer(code: string) {
	selectedCode.value = code
	showDetails.value = true
}
</script>
