<template>
	<div :id="`customer-${customer.customer_code}`">
		<CardEntity :loading :highlighted="!!highlight">
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
							<Icon :name="UserTypeIcon" :size="14"></Icon>
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
									<Icon :name="LocationIcon" :size="13"></Icon>
								</template>
								<template #value>
									<div class="flex flex-wrap items-center gap-2">
										{{ addressLabel }}
										<Icon
											v-if="addressLabel !== '-'"
											:name="InfoIcon"
											:size="13"
											class="!opacity-80"
										></Icon>
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
							<Icon :name="PhoneIcon" :size="13"></Icon>
						</template>
						<template #value>
							{{ customerInfo?.phone || "-" }}
						</template>
					</Badge>

					<Badge v-if="customerInfo?.parent_customer_code" type="splitted" color="primary">
						<template #iconLeft>
							<Icon :name="ParentIcon" :size="13"></Icon>
						</template>
						<template #label>Parent</template>
						<template #value>
							{{ customerInfo?.parent_customer_code }}
						</template>
					</Badge>
				</div>
			</template>

			<template v-if="!hideCardActions" #footerExtra>
				<n-button size="small" @click.stop="showDetails = true">
					<template #icon>
						<Icon :name="DetailsIcon"></Icon>
					</template>
					Details
				</n-button>
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			content-class="!p-0"
			:style="{ maxWidth: 'min(1100px, 90vw)', minHeight: 'min(600px, 90vh)', overflow: 'hidden' }"
			:title="customerInfo?.customer_name"
			:bordered="false"
			segmented
		>
			<Transition :name="`slide-tabs-${selectedTabsGroup === 'customer' ? 'left' : 'right'}`">
				<n-tabs v-if="selectedTabsGroup === 'customer'" type="line" animated :tabs-padding="24" class="h-full">
					<n-tab-pane name="Info" tab="Info" display-directive="show:lazy">
						<CustomerInfo
							v-if="customerInfo"
							v-model:loading="loadingDelete"
							:customer="customerInfo"
							@delete="deletedItem()"
							@submitted="customerInfo = $event"
						/>
					</n-tab-pane>
					<n-tab-pane name="Provision" tab="Provision" display-directive="show:lazy">
						<CustomerProvision
							:customer-meta="customerMeta"
							:customer-code="customer.customer_code"
							:customer-name="customer.customer_name"
							@delete="customerMeta = null"
							@submitted="customerMeta = $event"
						/>
					</n-tab-pane>
					<n-tab-pane
						name="3rd Party Integrations"
						tab="3rd Party Integrations"
						display-directive="show:lazy"
					>
						<CustomerIntegrations
							:customer-code="customer.customer_code"
							:customer-name="customer.customer_name"
						/>
					</n-tab-pane>
					<n-tab-pane name="Network Connectors" tab="Network Connectors" display-directive="show:lazy">
						<CustomerNetworkConnectors
							:customer-code="customer.customer_code"
							:customer-name="customer.customer_name"
						/>
					</n-tab-pane>
					<n-tab-pane
						name="Notification Workflows"
						tab="Notification Workflows"
						display-directive="show:lazy"
					>
						<CustomerNotificationsWorkflows :customer-code="customer.customer_code" />
					</n-tab-pane>

					<template #suffix>
						<div
							v-if="customerPortainerStackId !== null"
							class="hover:text-primary cursor-pointer pr-8 text-sm"
							@click="selectedTabsGroup = 'wazuh_worker'"
						>
							Wazuh Worker
						</div>
						<div
							class="hover:text-primary cursor-pointer pr-8 text-sm"
							@click="selectedTabsGroup = 'agents'"
						>
							Agents
						</div>
					</template>
				</n-tabs>
				<n-tabs v-else-if="selectedTabsGroup === 'agents'" type="line" animated :tabs-padding="24">
					<template #prefix>
						<div
							class="hover:text-primary relative top-1 cursor-pointer pl-6"
							@click="selectedTabsGroup = 'customer'"
						>
							<Icon :name="ArrowIcon" :size="20"></Icon>
						</div>
					</template>
					<n-tab-pane name="Agents" tab="Agents" display-directive="show:lazy">
						<n-scrollbar style="max-height: 470px" trigger="none">
							<div class="p-6 pt-2">
								<CustomerAgents v-if="customerInfo" :customer="customerInfo" />
							</div>
						</n-scrollbar>
					</n-tab-pane>
					<n-tab-pane name="Healthcheck Wazuh" tab="Healthcheck Wazuh" display-directive="show:lazy">
						<n-scrollbar style="max-height: 470px" trigger="none">
							<div class="p-6 pt-2">
								<CustomerHealthcheckList source="wazuh" :customer-code="customer.customer_code" />
							</div>
						</n-scrollbar>
					</n-tab-pane>
					<n-tab-pane
						name="Healthcheck Velociraptor"
						tab="Healthcheck Velociraptor"
						display-directive="show:lazy"
					>
						<n-scrollbar style="max-height: 470px" trigger="none">
							<div class="p-6 pt-2">
								<CustomerHealthcheckList
									source="velociraptor"
									:customer-code="customer.customer_code"
								/>
							</div>
						</n-scrollbar>
					</n-tab-pane>
				</n-tabs>
				<n-tabs v-else-if="selectedTabsGroup === 'wazuh_worker'" type="line" animated :tabs-padding="24">
					<template #prefix>
						<div
							class="hover:text-primary relative top-1 cursor-pointer pl-6"
							@click="selectedTabsGroup = 'customer'"
						>
							<Icon :name="ArrowIcon" :size="20"></Icon>
						</div>
					</template>
					<n-tab-pane name="Wazuh Worker" tab="Wazuh Worker" display-directive="show:lazy">
						<div class="px-7 py-4">
							<CustomerWazuhWorker v-if="customerPortainerStackId" :stack-id="customerPortainerStackId" />
						</div>
					</n-tab-pane>
				</n-tabs>
			</Transition>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { Customer, CustomerMeta } from "@/types/customers.d"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { hashMD5 } from "@/utils"
import _toSafeInteger from "lodash-es/toSafeInteger"
import { NAvatar, NButton, NModal, NPopover, NScrollbar, NTabPane, NTabs, useMessage } from "naive-ui"
import { computed, defineAsyncComponent, onBeforeMount, ref, toRefs, watch } from "vue"

const props = defineProps<{
	customer: Customer
	highlight?: boolean | null | undefined
	hideCardActions?: boolean | null | undefined
}>()
const emit = defineEmits<{
	(e: "delete"): void
}>()
const CustomerInfo = defineAsyncComponent(() => import("./CustomerInfo.vue"))
const CustomerAgents = defineAsyncComponent(() => import("./CustomerAgents.vue"))
const CustomerProvision = defineAsyncComponent(() => import("./provision/CustomerProvision.vue"))
const CustomerHealthcheckList = defineAsyncComponent(() => import("./healthcheck/CustomerHealthcheckList.vue"))
const CustomerIntegrations = defineAsyncComponent(() => import("./integrations/CustomerIntegrations.vue"))
const CustomerNetworkConnectors = defineAsyncComponent(
	() => import("./networkConnectors/CustomerNetworkConnectors.vue")
)
const CustomerNotificationsWorkflows = defineAsyncComponent(
	() => import("./notifications/CustomerNotificationsWorkflows.vue")
)
const CustomerWazuhWorker = defineAsyncComponent(() => import("./CustomerWazuhWorker.vue"))

const { customer, highlight, hideCardActions } = toRefs(props)

const DetailsIcon = "carbon:settings-adjust"
const UserTypeIcon = "solar:shield-user-linear"
const ParentIcon = "material-symbols-light:supervisor-account-outline-rounded"
const InfoIcon = "carbon:information"
const ArrowIcon = "carbon:arrow-left"
const LocationIcon = "carbon:location"
const PhoneIcon = "carbon:phone"

const showDetails = ref(false)
const selectedTabsGroup = ref<"customer" | "agents" | "wazuh_worker">("customer")
const loadingFull = ref(false)
const loadingDelete = ref(false)
const message = useMessage()
const customerInfo = ref<Customer | null>(null)
const customerMeta = ref<CustomerMeta | null>(null)
const customerPortainerStackId = ref<number | null>(null)

const loading = computed(() => loadingFull.value || loadingDelete.value)
const fallbackAvatar = computed(() => {
	let text = customer.value.customer_name.slice(0, 2).toUpperCase()

	if (customer.value.customer_name.includes(" ")) {
		const chunks = customer.value.customer_name.split(" ")
		text = (chunks[0][0] + chunks[1][0]).toUpperCase()
	}

	const hash = hashMD5(customer.value.customer_code)
	const uniq = hash.split("").find(o => _toSafeInteger(o).toString() === o)
	const seed = hash.slice(0, _toSafeInteger(uniq))

	return `https://avatar.vercel.sh/${seed}.svg?text=${text}`
})
const addressLabel = computed(
	() => [customerInfo.value?.city, customerInfo.value?.state].filter(o => !!o).join(", ") || "-"
)

function getFull() {
	loadingFull.value = true

	Api.customers
		.getCustomerFull(customer.value.customer_code)
		.then(res => {
			if (res.data.success) {
				customerInfo.value = res.data.customer
				customerMeta.value = res.data.customer_meta || null
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingFull.value = false
		})
}

function getPortainerStackId() {
	Api.portainer.getCustomerStackId(customer.value.customer_name).then(res => {
		if (res.data.success) {
			customerPortainerStackId.value = res.data.stack_id || null
		} else {
			message.warning(res.data?.message || "An error occurred. Please try again later.")
		}
	})
}

function deletedItem() {
	showDetails.value = false
	emit("delete")
}

watch(showDetails, val => {
	if (val) {
		selectedTabsGroup.value = "customer"

		if (
			customer.value.customer_code &&
			(!customer.value.customer_name || !customerMeta.value?.customer_meta_graylog_index)
		) {
			getFull()
		}

		if (!customerPortainerStackId.value) {
			getPortainerStackId()
		}
	}
})

onBeforeMount(() => {
	customerInfo.value = customer.value

	if (customer.value.customer_code && !customer.value.customer_name) {
		getFull()
	}
})
</script>

<style>
.slide-tabs-right-enter-active,
.slide-tabs-right-leave-active,
.slide-tabs-left-enter-active,
.slide-tabs-left-leave-active {
	transition: all 0.2s ease-out;
	position: absolute;
}

.slide-tabs-left-enter-from {
	transform: translateX(-100%);
}

.slide-tabs-left-leave-to {
	transform: translateX(100%);
}

.slide-tabs-right-enter-from {
	transform: translateX(100%);
}

.slide-tabs-right-leave-to {
	transform: translateX(-100%);
}
</style>
