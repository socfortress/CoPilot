<template>
	<div class="customer-healthcheck-item">
		<div class="px-4 py-3 flex flex-col gap-2">
			<div class="header-box flex justify-between items-center">
				<div class="id flex items-center gap-2 cursor-pointer" @click="showDetails = true">
					<span>#{{ healthData.id }} - {{ healthData.label }}</span>
					<Icon :name="InfoIcon" :size="16"></Icon>
				</div>
				<div class="time" v-if="cardDate">
					{{ cardDate }}
				</div>
			</div>

			<div class="main-box">
				<div class="content flex flex-col gap-1 grow">
					<div class="title">
						<Icon :name="InfoIcon" :size="14" class="mr-1 relative top-0.5"></Icon>
						{{ healthData.os }}
					</div>
					<div class="description">
						{{ healthData.ip_address }}
					</div>
				</div>
			</div>

			<div class="badges-box flex flex-wrap items-center gap-3 mt-2">
				<!--
				<Badge type="splitted">
					<template #iconLeft>
						<Icon :name="UserTypeIcon" :size="14"></Icon>
					</template>
					<template #label>Type</template>
					<template #value>{{ customerInfo?.customer_type || "-" }}</template>
				</Badge>
				<n-popover trigger="hover">
					<template #trigger>
						<Badge type="splitted" class="cursor-help">
							<template #iconLeft>
								<Icon :name="LocationIcon" :size="13"></Icon>
							</template>
							<template #value>
								{{ [customerInfo?.city, customerInfo?.state].join(", ") || "-" }}
							</template>
						</Badge>
					</template>

					<div class="flex flex-col gap-1">
						<div class="box">
							address_line1:
							<code>{{ customerInfo?.address_line1 }}</code>
						</div>
						<div class="box">
							address_line2:
							<code>{{ customerInfo?.address_line2 }}</code>
						</div>
						<div class="box">
							postal_code:
							<code>{{ customerInfo?.postal_code }}</code>
						</div>
						<div class="box">
							city:
							<code>{{ customerInfo?.city }}</code>
						</div>
						<div class="box">
							state:
							<code>{{ customerInfo?.state }}</code>
						</div>
						<div class="box">
							country:
							<code>{{ customerInfo?.country }}</code>
						</div>
					</div>
				</n-popover>
				<Badge type="splitted">
					<template #iconLeft>
						<Icon :name="PhoneIcon" :size="13"></Icon>
					</template>
					<template #value>{{ customerInfo?.phone || "-" }}</template>
				</Badge>
			-->
				<Badge type="splitted" v-if="healthData.agent_id">
					<template #iconLeft>
						<Icon :name="AgentIcon" :size="13"></Icon>
					</template>
					<template #label>Agent</template>
					<template #value>{{ healthData.hostname }}</template>
				</Badge>
				<Badge
					v-if="healthData.agent_id"
					type="active"
					@click="gotoAgentPage(healthData.agent_id)"
					class="cursor-pointer"
				>
					<template #iconRight>
						<Icon :name="LinkIcon" :size="14"></Icon>
					</template>
					<template #label>Agent #{{ healthData.hostname }}</template>
				</Badge>

				<n-popover overlap placement="bottom-start">
					<template #trigger>
						<Badge type="splitted" hint-cursor>
							<template #iconLeft>
								<Icon :name="AgentIcon" :size="13" class="!opacity-80"></Icon>
							</template>
							<template #label>Agent</template>
							<template #value>
								{{ healthData.hostname }}
							</template>
						</Badge>
					</template>
					<div class="flex flex-col gap-1">
						<div class="box">
							agent_id:
							<code class="cursor-pointer text-primary-color" @click="gotoAgentPage(healthData.agent_id)">
								{{ healthData.agent_id }}
								<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
							</code>
						</div>
						<div class="box">
							hostname:
							<code>{{ healthData.hostname }}</code>
						</div>
					</div>
				</n-popover>
			</div>
		</div>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			content-style="padding:0px"
			:style="{ maxWidth: 'min(800px, 90vw)', overflow: 'hidden' }"
			:title="`Health check ${type}`"
			:bordered="false"
			segmented
		>
			<div class="grid gap-2 grid-auto-flow-200 px-7 py-6">
				<KVCard v-for="(value, key) of healthData" :key="key">
					<template #key>{{ key }}</template>
					<template #value>{{ value || "-" }}</template>
				</KVCard>
			</div>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import Badge from "@/components/common/Badge.vue"
import { computed, onBeforeMount, ref, toRefs, watch } from "vue"
import CustomerInfoComponent from "./CustomerInfo.vue"
import KVCard from "@/components/common/KVCard.vue"
import CustomerMetaComponent from "./CustomerMeta.vue"
import CustomerAgents from "./CustomerAgents.vue"
import CustomerHealthcheck from "./CustomerHealthcheck.vue"
import Api from "@/api"
import { NAvatar, useMessage, NPopover, NModal, NTabs, NTabPane, NSpin } from "naive-ui"
import type { Customer, CustomerAgentHealth, CustomerHealthcheckType, CustomerMeta } from "@/types/customers.d"
import dayjs from "@/utils/dayjs"
import { useSettingsStore } from "@/stores/settings"
import { useRouter } from "vue-router"

const { healthData, type } = defineProps<{
	healthData: CustomerAgentHealth
	type: CustomerHealthcheckType
}>()

const InfoIcon = "carbon:information"
const DetailsIcon = "carbon:settings-adjust"
const UserTypeIcon = "solar:shield-user-linear"
const ParentIcon = "material-symbols-light:supervisor-account-outline-rounded"
const LocationIcon = "carbon:location"
const AgentIcon = "carbon:police"
const LinkIcon = "carbon:launch"
const PhoneIcon = "carbon:phone"

const showDetails = ref(false)
const loadingFull = ref(false)
const loadingDelete = ref(false)
const router = useRouter()
const message = useMessage()
const customerInfo = ref<Customer | null>(null)
const customerMeta = ref<CustomerMeta | null>(null)
const cardDate = computed(() => {
	let date = ""
	switch (type) {
		case "wazuh":
			date = healthData.wazuh_last_seen
			break
		case "velociraptor":
			date = healthData.velociraptor_last_seen
			break
	}

	return date ? formatDate(date) : ""
})

const dFormats = useSettingsStore().dateFormat

function formatDate(timestamp: string | number, utc: boolean = true): string {
	return dayjs(timestamp).utc(utc).format(dFormats.datetimesec)
}

function gotoAgentPage(agentId: string) {
	router.push(`/agent/${agentId}`).catch(() => {})
}
</script>

<style lang="scss" scoped>
.customer-healthcheck-item {
	border-radius: var(--border-radius);
	background-color: var(--bg-color);
	transition: all 0.2s var(--bezier-ease);
	border: var(--border-small-050);

	.header-box {
		font-family: var(--font-family-mono);
		font-size: 13px;

		.id {
			word-break: break-word;
			color: var(--fg-secondary-color);
			line-height: 1.2;

			&:hover {
				color: var(--primary-color);
			}
		}

		.time {
			color: var(--fg-secondary-color);
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
