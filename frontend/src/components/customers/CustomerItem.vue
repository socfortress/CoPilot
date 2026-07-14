<template>
	<div :id="`customer-${customer.customer_code}`">
		<CardEntity :loading :highlighted="!!highlight" :hide-footer-extra="!!hideCardActions">
			<template #default>
				<div class="flex items-start gap-4">
					<n-avatar
						:src="customerInfo?.logo_file || fallbackAvatar"
						:fallback-src="fallbackAvatar"
						round
						:size="40"
					/>

					<div class="flex flex-col gap-1">
						<div class="flex flex-wrap gap-2">
							{{ customerInfo?.customer_name }}
							<span class="text-secondary">#{{ customer.customer_code }}</span>
						</div>
						<p class="text-sm">
							{{ customerInfo?.contact_first_name }} {{ customerInfo?.contact_last_name }}
						</p>
					</div>
				</div>
			</template>

			<template #footerMain>
				<div class="flex flex-wrap items-center gap-3">
					<Badge type="splitted" color="primary">
						<template #iconLeft>
							<Icon :name="UserTypeIcon" :size="14" />
						</template>
						<template #label>Type</template>
						<template #value>
							{{ customerInfo?.customer_type || "-" }}
						</template>
					</Badge>

					<n-popover trigger="hover" :disabled="addressLabel === '-'">
						<template #trigger>
							<Badge type="splitted" color="primary" :class="{ 'cursor-help': addressLabel !== '-' }">
								<template #iconLeft>
									<Icon :name="LocationIcon" :size="13" />
								</template>
								<template #value>
									<div class="flex flex-wrap items-center gap-2">
										{{ addressLabel }}
										<Icon
											v-if="addressLabel !== '-'"
											:name="InfoIcon"
											:size="13"
											class="opacity-80!"
										/>
									</div>
								</template>
							</Badge>
						</template>

						<div class="flex flex-col gap-1">
							<div v-if="customerInfo?.address_line1" class="box">
								address_line1:
								<code>{{ customerInfo.address_line1 }}</code>
							</div>
							<div v-if="customerInfo?.address_line2" class="box">
								address_line2:
								<code>{{ customerInfo.address_line2 }}</code>
							</div>
							<div v-if="customerInfo?.postal_code" class="box">
								postal_code:
								<code>{{ customerInfo.postal_code }}</code>
							</div>
							<div v-if="customerInfo?.city" class="box">
								city:
								<code>{{ customerInfo.city }}</code>
							</div>
							<div v-if="customerInfo?.state" class="box">
								state:
								<code>{{ customerInfo.state }}</code>
							</div>
							<div v-if="customerInfo?.country" class="box">
								country:
								<code>{{ customerInfo.country }}</code>
							</div>
						</div>
					</n-popover>

					<Badge type="splitted" color="primary">
						<template #iconLeft>
							<Icon :name="PhoneIcon" :size="13" />
						</template>
						<template #value>
							{{ customerInfo?.phone || "-" }}
						</template>
					</Badge>

					<Badge v-if="customerInfo?.parent_customer_code" type="splitted" color="primary">
						<template #iconLeft>
							<Icon :name="ParentIcon" :size="13" />
						</template>
						<template #label>Parent</template>
						<template #value>
							{{ customerInfo?.parent_customer_code }}
						</template>
					</Badge>

					<Badge type="splitted" :color="customer.is_provisioned ? 'success' : 'danger'" bright>
						<template #iconLeft>
							<Icon :name="ProvisionIcon" :size="13" />
						</template>
						<template #label>Status</template>
						<template #value>
							{{ customer.is_provisioned ? "Provisioned" : "Not Provisioned" }}
						</template>
					</Badge>

					<Badge v-if="customer.is_provisioned && agentCount !== null" type="splitted" color="primary">
						<template #iconLeft>
							<Icon :name="AgentsIcon" :size="13" />
						</template>
						<template #label>Agents</template>
						<template #value>
							{{ agentCount }}
						</template>
					</Badge>
				</div>
			</template>

			<template #footerExtra>
				<EntityDetailsButton
					size="small"
					:route="routeCustomer({ code: customer.customer_code })"
					@view="showDetails = true"
				/>
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			content-class="p-0!"
			:style="{ maxWidth: 'min(1100px, 90vw)', minHeight: 'min(470px, 90vh)', overflow: 'hidden' }"
			:title="customerInfo?.customer_name"
			:bordered="false"
			segmented
		>
			<CustomerDetails v-if="showDetails" :customer use-max-height @delete="deletedItem()" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { Customer } from "@/types/customers"
import { NAvatar, NModal, NPopover, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, toRefs } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import EntityDetailsButton from "@/components/common/EntityDetailsButton.vue"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/useNavigation"
import { getApiErrorMessage, getAvatar, getNameInitials } from "@/utils"
import CustomerDetails from "./CustomerDetails.vue"

const props = defineProps<{
	customer: Customer
	highlight?: boolean | null | undefined
	hideCardActions?: boolean | null | undefined
}>()
const emit = defineEmits<{
	(e: "delete"): void
}>()

const { customer, highlight, hideCardActions } = toRefs(props)

const UserTypeIcon = "solar:shield-user-linear"
const ParentIcon = "material-symbols-light:supervisor-account-outline-rounded"
const InfoIcon = "carbon:information"
const LocationIcon = "carbon:location"
const PhoneIcon = "carbon:phone"
const ProvisionIcon = "carbon:network-3"
const AgentsIcon = "carbon:devices"

const { routeCustomer } = useNavigation()
const showDetails = ref(false)
const loading = ref(false)
const message = useMessage()
const customerInfo = ref<Customer | null>(null)
const agentCount = ref<number | null>(null)

const fallbackAvatar = computed(() => {
	const initials = getNameInitials(customer.value.customer_name)
	return getAvatar({ seed: initials, text: initials })
})

const addressLabel = computed(
	() => [customerInfo.value?.city, customerInfo.value?.state].filter(o => !!o).join(", ") || "-"
)

function getFull() {
	loading.value = true

	Api.customers
		.getCustomerFull(customer.value.customer_code)
		.then(res => {
			if (res.data.success) {
				customerInfo.value = res.data.customer
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

function getAgentCount() {
	Api.customers
		.getCustomerAgents(customer.value.customer_code)
		.then(res => {
			if (res.data.success) {
				agentCount.value = res.data.agents?.length || 0
			}
		})
		.catch(err => {
			console.error("Failed to fetch agent count:", err)
		})
}

function deletedItem() {
	showDetails.value = false
	emit("delete")
}

onBeforeMount(() => {
	customerInfo.value = customer.value

	if (customer.value.customer_code && !customer.value.customer_name) {
		getFull()
	}

	if (customer.value.is_provisioned) {
		getAgentCount()
	}
})
</script>
