<template>
	<n-spin :show="loading" :class="{ highlight }" :id="'customer-' + customer.customer_code" class="customer-item">
		<div class="px-4 py-3 flex flex-col gap-2">
			<div class="header-box flex justify-between items-center">
				<div class="id">#{{ customer.customer_code }}</div>
				<div class="actions" v-if="!hideCardActions">
					<n-button size="small" @click.stop="showDetails = true">
						<template #icon>
							<Icon :name="DetailsIcon"></Icon>
						</template>
						Details
					</n-button>
				</div>
			</div>
			<div class="main-box flex items-center gap-3">
				<n-avatar
					:src="customerInfo?.logo_file || fallbackAvatar"
					:fallback-src="fallbackAvatar"
					round
					:size="40"
				/>

				<div class="content flex flex-col gap-1 grow">
					<div class="title">{{ customerInfo?.customer_name }}</div>
					<div class="description">
						{{ customerInfo?.contact_first_name }} {{ customerInfo?.contact_last_name }}
					</div>
				</div>
			</div>

			<div class="badges-box flex flex-wrap items-center gap-3 mt-2">
				<Badge type="splitted">
					<template #iconLeft>
						<Icon :name="UserTypeIcon" :size="14"></Icon>
					</template>
					<template #label>Type</template>
					<template #value>{{ customerInfo?.customer_type || "-" }}</template>
				</Badge>

				<n-popover trigger="hover" :disabled="addressLabel === '-'">
					<template #trigger>
						<Badge type="splitted" :class="{ 'cursor-help': addressLabel !== '-' }">
							<template #iconLeft>
								<Icon :name="LocationIcon" :size="13"></Icon>
							</template>
							<template #value>
								{{ addressLabel }}
							</template>
						</Badge>
					</template>

					<div class="flex flex-col gap-1">
						<div class="box" v-if="customerInfo?.address_line1">
							address_line1:
							<code>{{ customerInfo.address_line1 }}</code>
						</div>
						<div class="box" v-if="customerInfo?.address_line2">
							address_line2:
							<code>{{ customerInfo.address_line2 }}</code>
						</div>
						<div class="box" v-if="customerInfo?.postal_code">
							postal_code:
							<code>{{ customerInfo.postal_code }}</code>
						</div>
						<div class="box" v-if="customerInfo?.city">
							city:
							<code>{{ customerInfo.city }}</code>
						</div>
						<div class="box" v-if="customerInfo?.state">
							state:
							<code>{{ customerInfo.state }}</code>
						</div>
						<div class="box" v-if="customerInfo?.country">
							country:
							<code>{{ customerInfo.country }}</code>
						</div>
					</div>
				</n-popover>

				<Badge type="splitted">
					<template #iconLeft>
						<Icon :name="PhoneIcon" :size="13"></Icon>
					</template>
					<template #value>{{ customerInfo?.phone || "-" }}</template>
				</Badge>

				<Badge type="splitted" v-if="customerInfo?.parent_customer_code">
					<template #iconLeft>
						<Icon :name="ParentIcon" :size="13"></Icon>
					</template>
					<template #label>Parent</template>
					<template #value>{{ customerInfo?.parent_customer_code }}</template>
				</Badge>
			</div>
		</div>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			content-class="!p-0"
			:style="{ maxWidth: 'min(900px, 90vw)', minHeight: 'min(600px, 90vh)', overflow: 'hidden' }"
			:title="customerInfo?.customer_name"
			:bordered="false"
			segmented
		>
			<Transition :name="`slide-tabs-${selectedTabsGroup === 'customer' ? 'left' : 'right'}`">
				<n-tabs type="line" animated :tabs-padding="24" v-if="selectedTabsGroup === 'customer'" class="h-full">
					<n-tab-pane name="Info" tab="Info" display-directive="show:lazy">
						<CustomerInfo
							:customer="customerInfo"
							@delete="deletedItem()"
							@submitted="customerInfo = $event"
							v-model:loading="loadingDelete"
							v-if="customerInfo"
						/>
					</n-tab-pane>
					<n-tab-pane name="Provision" tab="Provision" display-directive="show:lazy">
						<CustomerProvision
							:customerMeta="customerMeta"
							:customerCode="customer.customer_code"
							:customerName="customer.customer_name"
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
							:customerCode="customer.customer_code"
							:customerName="customer.customer_name"
						/>
					</n-tab-pane>
					<n-tab-pane name="Network Connectors" tab="Network Connectors" display-directive="show:lazy">
						<CustomerNetworkConnectors
							:customerCode="customer.customer_code"
							:customerName="customer.customer_name"
						/>
					</n-tab-pane>
					<template #suffix>
						<div class="pr-8 hover:text-primary-color cursor-pointer" @click="selectedTabsGroup = 'agents'">
							Agents
						</div>
					</template>
				</n-tabs>
				<n-tabs type="line" animated :tabs-padding="24" v-else-if="selectedTabsGroup === 'agents'">
					<template #prefix>
						<div
							class="pl-6 relative top-1 hover:text-primary-color cursor-pointer"
							@click="selectedTabsGroup = 'customer'"
						>
							<Icon :name="ArrowIcon" :size="20"></Icon>
						</div>
					</template>
					<n-tab-pane name="Agents" tab="Agents" display-directive="show:lazy">
						<n-scrollbar style="max-height: 470px" trigger="none">
							<div class="p-6 pt-2">
								<CustomerAgents :customer="customerInfo" v-if="customerInfo" />
							</div>
						</n-scrollbar>
					</n-tab-pane>
					<n-tab-pane name="Healthcheck Wazuh" tab="Healthcheck Wazuh" display-directive="show:lazy">
						<n-scrollbar style="max-height: 470px" trigger="none">
							<div class="p-6 pt-2">
								<CustomerHealthcheckList source="wazuh" :customerCode="customer.customer_code" />
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
								<CustomerHealthcheckList source="velociraptor" :customerCode="customer.customer_code" />
							</div>
						</n-scrollbar>
					</n-tab-pane>
				</n-tabs>
			</Transition>
		</n-modal>
	</n-spin>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import Badge from "@/components/common/Badge.vue"
import { computed, onBeforeMount, ref, toRefs, watch } from "vue"
import CustomerInfo from "./CustomerInfo.vue"
import CustomerAgents from "./CustomerAgents.vue"
import CustomerProvision from "./provision/CustomerProvision.vue"
import CustomerHealthcheckList from "./healthcheck/CustomerHealthcheckList.vue"
import CustomerIntegrations from "./integrations/CustomerIntegrations.vue"
import CustomerNetworkConnectors from "./networkConnectors/CustomerNetworkConnectors.vue"
import Api from "@/api"
import { NAvatar, useMessage, NPopover, NModal, NTabs, NTabPane, NSpin, NScrollbar, NButton } from "naive-ui"
import type { Customer, CustomerMeta } from "@/types/customers.d"
import { hashMD5 } from "@/utils"
import _toSafeInteger from "lodash/toSafeInteger"

const emit = defineEmits<{
	(e: "delete"): void
}>()

const props = defineProps<{
	customer: Customer
	highlight?: boolean | null | undefined
	hideCardActions?: boolean | null | undefined
}>()
const { customer, highlight, hideCardActions } = toRefs(props)

const DetailsIcon = "carbon:settings-adjust"
const UserTypeIcon = "solar:shield-user-linear"
const ParentIcon = "material-symbols-light:supervisor-account-outline-rounded"
const ArrowIcon = "carbon:arrow-left"
const LocationIcon = "carbon:location"
const PhoneIcon = "carbon:phone"

const showDetails = ref(false)
const selectedTabsGroup = ref<"customer" | "agents">("customer")
const loadingFull = ref(false)
const loadingDelete = ref(false)
const message = useMessage()
const customerInfo = ref<Customer | null>(null)
const customerMeta = ref<CustomerMeta | null>(null)

const loading = computed(() => loadingFull.value || loadingDelete.value)
const fallbackAvatar = computed(() => {
	let text = customer.value.customer_name.slice(0, 2).toUpperCase()

	if (customer.value.customer_name.indexOf(" ") !== -1) {
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
	}
})

onBeforeMount(() => {
	customerInfo.value = customer.value

	if (customer.value.customer_code && !customer.value.customer_name) {
		getFull()
	}
})
</script>

<style lang="scss" scoped>
.customer-item {
	border-radius: var(--border-radius);
	background-color: var(--bg-color);
	transition: all 0.2s var(--bezier-ease);
	border: var(--border-small-050);

	.header-box {
		font-size: 13px;
		.id {
			font-family: var(--font-family-mono);
			word-break: break-word;
			color: var(--fg-secondary-color);
			line-height: 1.2;
		}
	}

	.main-box {
		.content {
			word-break: break-word;

			.description {
				color: var(--fg-secondary-color);
				font-size: 13px;
			}
		}
	}

	&.highlight,
	&:hover {
		box-shadow: 0px 0px 0px 1px inset var(--primary-color);
	}
}
</style>

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
