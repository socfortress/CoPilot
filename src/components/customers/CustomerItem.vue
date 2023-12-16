<template>
	<n-spin :show="loadingFull" :class="{ highlight }" :id="'customer-' + customer.customer_code" class="customer-item">
		<div class="px-4 py-3 flex flex-col gap-2">
			<div class="header-box flex justify-between items-center">
				<div class="id">#{{ customer.customer_code }}</div>
				<div class="actions">
					<Badge type="cursor" @click="showDetails = true">
						<template #iconLeft>
							<Icon :name="DetailsIcon" :size="14"></Icon>
						</template>
						<template #value>Details</template>
					</Badge>
				</div>
			</div>
			<div class="main-box flex items-center gap-3">
				<n-avatar :src="customer.logo_file" fallback-src="/images/img-not-found.svg" round :size="40" lazy />

				<div class="content flex flex-col gap-1 grow">
					<div class="title">{{ customer.customer_name }}</div>
					<div class="description">{{ customer.contact_first_name }} {{ customer.contact_last_name }}</div>
				</div>
			</div>

			<div class="badges-box flex flex-wrap items-center gap-3 mt-2">
				<Badge type="splitted">
					<template #iconLeft>
						<Icon :name="UserTypeIcon" :size="14"></Icon>
					</template>
					<template #label>Type</template>
					<template #value>{{ customer.customer_type || "-" }}</template>
				</Badge>
				<n-popover trigger="hover">
					<template #trigger>
						<Badge type="splitted" class="cursor-help">
							<template #iconLeft>
								<Icon :name="LocationIcon" :size="13"></Icon>
							</template>
							<template #value>{{ [customer.city, customer.state].join(", ") || "-" }}</template>
						</Badge>
					</template>

					<div class="flex flex-col gap-1">
						<div class="box">
							address_line1:
							<code>{{ customer.address_line1 }}</code>
						</div>
						<div class="box">
							address_line2:
							<code>{{ customer.address_line2 }}</code>
						</div>
						<div class="box">
							postal_code:
							<code>{{ customer.postal_code }}</code>
						</div>
						<div class="box">
							city:
							<code>{{ customer.city }}</code>
						</div>
						<div class="box">
							state:
							<code>{{ customer.state }}</code>
						</div>
						<div class="box">
							country:
							<code>{{ customer.country }}</code>
						</div>
					</div>
				</n-popover>
				<Badge type="splitted">
					<template #iconLeft>
						<Icon :name="PhoneIcon" :size="13"></Icon>
					</template>
					<template #value>{{ customer.phone || "-" }}</template>
				</Badge>
				<Badge type="splitted" v-if="customer.parent_customer_code">
					<template #iconLeft>
						<Icon :name="ParentIcon" :size="13"></Icon>
					</template>
					<template #label>Parent</template>
					<template #value>{{ customer.parent_customer_code }}</template>
				</Badge>
			</div>

			<n-modal
				v-model:show="showDetails"
				preset="card"
				content-style="padding:0px"
				:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(600px, 90vh)', overflow: 'hidden' }"
				:title="customer.customer_name"
				:bordered="false"
				segmented
			>
				<n-tabs type="line" animated :tabs-padding="24">
					<n-tab-pane name="Info" tab="Info" display-directive="show:lazy">
						<div class="flex items-center justify-between gap-4 px-7 pt-2">
							<n-button size="small">
								<template #icon>
									<Icon :name="EditIcon" :size="14"></Icon>
								</template>
								Edit
							</n-button>
							<n-button size="small" type="error" ghost @click.stop="handleDelete">
								<template #icon>
									<Icon :name="DeleteIcon" :size="15"></Icon>
								</template>
								Delete Customer
							</n-button>
						</div>
						<div class="grid gap-2 grid-auto-flow-200 p-7 pt-4">
							<KVCard v-for="(value, key) of customer" :key="key">
								<template #key>{{ key }}</template>
								<template #value>{{ value ?? "-" }}</template>
							</KVCard>
						</div>
					</n-tab-pane>
					<n-tab-pane name="Meta" tab="Meta" display-directive="show:lazy">
						<div class="flex items-center justify-between gap-4 px-7 pt-2">
							<n-button size="small">
								<template #icon>
									<Icon :name="EditIcon" :size="14"></Icon>
								</template>
								Edit
							</n-button>
							<n-button size="small" type="error" ghost>
								<template #icon>
									<Icon :name="DeleteIcon" :size="15"></Icon>
								</template>
								Clear Meta
							</n-button>
						</div>
						<div class="grid gap-2 grid-auto-flow-250 p-7 pt-4" v-if="customerMeta">
							<KVCard v-for="(value, key) of customerMeta" :key="key">
								<template #key>{{ key }}</template>
								<template #value>{{ value || "-" }}</template>
							</KVCard>
						</div>
						<div v-else>add</div>
					</n-tab-pane>
					<n-tab-pane name="Agents" tab="Agents" display-directive="show:lazy">
						<CustomerAgents :customer="customer" />
					</n-tab-pane>
					<n-tab-pane name="Healthcheck Wazuh" tab="Healthcheck Wazuh" display-directive="show:lazy">
						Healthcheck Wazuh
					</n-tab-pane>
					<n-tab-pane
						name="Healthcheck Velociraptor"
						tab="Healthcheck Velociraptor"
						display-directive="show:lazy"
					>
						Healthcheck Velociraptor
					</n-tab-pane>
				</n-tabs>
			</n-modal>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
// TODO: add mablibre on location popup ??

import AlertItem from "@/components/alerts/Alert.vue"
import type { SocAlert } from "@/types/soc/alert.d"
import type { Alert } from "@/types/alerts.d"
import Icon from "@/components/common/Icon.vue"
import Badge from "@/components/common/Badge.vue"
import { computed, h, onBeforeMount, ref, toRefs, watch } from "vue"
import KVCard from "@/components/common/KVCard.vue"
import AgentCard from "@/components/agents/AgentCard.vue"
import CustomerAgents from "./CustomerAgents.vue"
import Api from "@/api"
import {
	NImage,
	NAvatar,
	useMessage,
	NCollapseItem,
	NPopover,
	NModal,
	NTabs,
	NTabPane,
	NSpin,
	NButton,
	NTooltip,
	useDialog
} from "naive-ui"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"
import type { SocUser } from "@/types/soc/user.d"
import type { Customer, CustomerMeta } from "@/types/customers.d"
import { useRouter } from "vue-router"
import type { Agent } from "@/types/agents.d"
import { isAgentOnline } from "@/components/agents/utils"

const emit = defineEmits<{
	(e: "bookmark"): void
}>()

const props = defineProps<{
	customer: Customer
	highlight?: boolean | null | undefined
}>()
const { customer, highlight } = toRefs(props)

const DetailsIcon = "carbon:settings-adjust"
const UserTypeIcon = "solar:shield-user-linear"
const ParentIcon = "material-symbols-light:supervisor-account-outline-rounded"
const LocationIcon = "carbon:location"
const PhoneIcon = "carbon:phone"
const ChevronIcon = "carbon:chevron-right"
const InfoIcon = "carbon:information"
const TimeIcon = "carbon:time"
const LinkIcon = "carbon:launch"
const StatusIcon = "fluent:status-20-regular"
const SeverityIcon = "bi:shield-exclamation"
const SourceIcon = "lucide:arrow-down-right-from-circle"
const CustomerIcon = "carbon:user"
const StarActiveIcon = "carbon:star-filled"
const OwnerIcon = "carbon:user-military"
const StarIcon = "carbon:star"
const EditIcon = "uil:edit-alt"
const DeleteIcon = "ph:trash"

const showDetails = ref(false)
const loadingFull = ref(false)
const loadingAgents = ref(false)
const router = useRouter()
const dialog = useDialog()
const message = useMessage()
const customerMeta = ref<CustomerMeta | null>(null)
const customerAgents = ref<Agent[] | []>([])

function getFull() {
	loadingFull.value = true

	Api.customers
		.getCustomerFull(customer.value.customer_code)
		.then(res => {
			if (res.data.success) {
				customer.value = res.data.customer
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

function handleDelete() {
	dialog.warning({
		title: "Confirm",
		content: () =>
			h("div", {
				innerHTML: `Are you sure you want to delete the Customer:<br/><strong>${customer.value.customer_code}</strong> ?`
			}),
		positiveText: "Yes I'm sure",
		negativeText: "Cancel",
		onPositiveClick: () => {
			/// deleteAgent({ agent, cbBefore, cbSuccess, cbAfter, cbError, dialog, message })
		},
		onNegativeClick: () => {
			message.info("Delete canceled")
		}
	})
}

watch(showDetails, val => {
	if (val) {
		if (!customer.value.customer_name || !customerMeta.value?.customer_meta_graylog_index) {
			getFull()
		}
	}
})

onBeforeMount(() => {
	if (!customer.value.customer_name) {
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

	&.highlight {
		box-shadow: 0px 0px 0px 1px inset var(--primary-color);
	}
}
</style>
