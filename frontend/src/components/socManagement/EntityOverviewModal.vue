<template>
	<n-modal
		:show="!!target"
		preset="card"
		content-class="p-0!"
		:style="{ maxWidth: target?.kind === 'user' ? 'min(720px, 90vw)' : 'min(1100px, 90vw)', minHeight: 'min(470px, 90vh)', overflow: 'hidden' }"
		:title
		:bordered="false"
		segmented
		data-testid="entity-overview-modal"
		@update:show="show => !show && emit('close')"
	>
		<CustomerDetails
			v-if="target?.kind === 'customer'"
			:customer-code="target.key"
			use-max-height
			@loaded="customer => (customerName = customer.customer_name)"
			@delete="emit('close')"
		/>
		<div v-else-if="target?.kind === 'user'" class="p-4">
			<UserDetailsByUsername :username="target.key" @deleted="emit('close')" />
		</div>
	</n-modal>
</template>

<script setup lang="ts">
// The overview of a customer or a user, opened in place from a row that names one —
// the same details the Customers and Users pages show, without leaving the dashboard.
import { NModal } from "naive-ui"
import { computed, defineAsyncComponent, shallowRef, watch } from "vue"

export interface OverviewTarget {
	kind: "customer" | "user"
	/** The customer code, or the username. */
	key: string
}

const { target } = defineProps<{ target: OverviewTarget | null }>()
const emit = defineEmits<{ (e: "close"): void }>()

// Heavy pages of their own: loaded only when someone opens one.
const CustomerDetails = defineAsyncComponent(() => import("@/components/customers/CustomerDetails.vue"))
const UserDetailsByUsername = defineAsyncComponent(() => import("@/components/users/UserDetailsByUsername.vue"))

const customerName = shallowRef<string | null>(null)
watch(
	() => target?.key,
	() => {
		customerName.value = null
	}
)

const title = computed(() => {
	if (!target) return ""
	if (target.kind === "user") return `User · ${target.key}`
	return customerName.value ? `${customerName.value} · ${target.key}` : `Customer · ${target.key}`
})
</script>
