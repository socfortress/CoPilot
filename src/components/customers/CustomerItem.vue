<template>
	<n-spin :show="loading" :class="{ highlight }" :id="'customer-' + customer.customer_code" class="customer-item">
		<div class="px-5 py-3 flex flex-col gap-2">
			<div class="header-box flex justify-between">
				<div class="id flex items-center gap-2 cursor-pointer" @click="showDetails = true">
					<span>{{ customer.customer_code }}</span>
					<Icon :name="InfoIcon" :size="16"></Icon>
				</div>
			</div>
			<div class="main-box flex items-center gap-3">
				<n-avatar :src="customer.logo_file" fallback-src="/images/img-not-found.svg" round :size="40" lazy />

				<div class="content flex flex-col gap-1 grow">
					<div class="title">{{ customer.customer_name }}</div>
					<div class="description">{{ customer.contact_first_name }} {{ customer.contact_last_name }}</div>
				</div>
			</div>

			<!--
		<div class="badges-box flex flex-wrap items-center gap-3 mt-2">
			<Badge type="splitted" :color="alert.severity?.severity_id === 5 ? 'danger' : undefined">
				<template #iconLeft>
					<Icon :name="SeverityIcon" :size="13"></Icon>
				</template>
				<template #label>Severity</template>
				<template #value>{{ alert.severity?.severity_name || "-" }}</template>
			</Badge>
			<Badge type="splitted" class="hide-on-small">
				<template #iconLeft>
					<Icon :name="SourceIcon" :size="13"></Icon>
				</template>
				<template #label>Source</template>
				<template #value>{{ alert.alert_source || "-" }}</template>
			</Badge>
			<Badge type="splitted" class="hide-on-small">
				<template #iconLeft>
					<Icon :name="CustomerIcon" :size="13"></Icon>
				</template>
				<template #label>Customer</template>
				<template #value>{{ alert.customer?.customer_name || "-" }}</template>
			</Badge>


		</div>

		-->

			<!--
		<n-modal
			v-model:show="showDetails"
			preset="card"
			content-style="padding:0px"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(550px, 90vh)', overflow: 'hidden' }"
			:title="`#${alert.alert_id} - ${alert.alert_uuid}`"
			:bordered="false"
			segmented
		>
			<n-tabs type="line" animated justify-content="space-evenly">
				<n-tab-pane name="Context" tab="Context" display-directive="show:lazy">
					<div class="grid gap-2 soc-alert-context-grid p-7 pt-4">
						<KVCard v-for="(value, key) of alert.alert_context" :key="key">
							<template #key>{{ key }}</template>
							<template #value>{{ value ?? "-" }}</template>
						</KVCard>
					</div>
				</n-tab-pane>
				<n-tab-pane name="Note" tab="Note" display-directive="show:lazy">
					<div class="p-7 pt-4">
						{{ alert.alert_note }}
					</div>
				</n-tab-pane>
				<n-tab-pane name="Customer" tab="Customer" display-directive="show:lazy">
					<div class="grid gap-2 soc-alert-context-grid p-7 pt-4">
						<KVCard v-for="(value, key) of alert.customer" :key="key">
							<template #key>{{ key }}</template>
							<template #value>{{ value || "-" }}</template>
						</KVCard>
					</div>
				</n-tab-pane>
				<n-tab-pane name="Owner" tab="Owner" display-directive="show:lazy">
					<div class="grid gap-2 px-7 pt-4">
						<Badge
							type="active"
							style="max-width: 145px"
							class="cursor-pointer"
							@click="gotoUsersPage(ownerId)"
						>
							<template #iconRight>
								<Icon :name="LinkIcon" :size="14"></Icon>
							</template>
							<template #label>Go to users page</template>
						</Badge>
					</div>
					<div class="grid gap-2 soc-alert-context-grid p-7 pt-4">
						<KVCard>
							<template #key>user_login</template>
							<template #value>
								<SocAssignUser
									:alert="alert"
									:users="users"
									v-slot="{ loading }"
									@updated="updateAlert"
								>
									<div class="flex items-center gap-2 cursor-pointer text-primary-color">
										<n-spin :size="16" :show="loading">
											<Icon :name="EditIcon" :size="16"></Icon>
										</n-spin>
										<span>{{ ownerName || "Assign a user" }}</span>
									</div>
								</SocAssignUser>
							</template>
						</KVCard>
						<KVCard v-if="alert.owner">
							<template #key>user_name</template>
							<template #value>
								<span>#{{ alert.owner.id }}</span>
								{{ alert.owner.user_name }}
							</template>
						</KVCard>
						<KVCard v-if="alert.owner">
							<template #key>user_email</template>
							<template #value>
								{{ alert.owner.user_email }}
							</template>
						</KVCard>
					</div>
				</n-tab-pane>
				<n-tab-pane name="History" tab="History" display-directive="show:lazy">
					<div class="p-7 pt-4">
						<SocAlertTimeline :alert="alert" />
					</div>
				</n-tab-pane>
				<n-tab-pane name="Details" tab="Details" display-directive="show:lazy">
					<div class="p-7 pt-4">
						<SimpleJsonViewer
							class="vuesjv-override"
							:model-value="socAlertDetail"
							:initialExpandedDepth="1"
						/>
					</div>
				</n-tab-pane>
			</n-tabs>
		</n-modal>
		-->
		</div>
	</n-spin>
</template>

<script setup lang="ts">
// TODO: add mablibre popup for address badge

import AlertItem from "@/components/alerts/Alert.vue"
import type { SocAlert } from "@/types/soc/alert.d"
import type { Alert } from "@/types/alerts.d"
import Icon from "@/components/common/Icon.vue"
import Badge from "@/components/common/Badge.vue"
import { computed, onBeforeMount, ref, toRefs } from "vue"
import { SimpleJsonViewer } from "vue-sjv"
import KVCard from "@/components/common/KVCard.vue"
import SocAlertTimeline from "./SocAlertTimeline.vue"
import SocAssignUser from "./SocAssignUser.vue"
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
	NTooltip
} from "naive-ui"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"
import type { SocUser } from "@/types/soc/user.d"
import type { Customer } from "@/types/customers.d"
import { useRouter } from "vue-router"

const emit = defineEmits<{
	(e: "bookmark"): void
}>()

const props = defineProps<{
	customer: Customer
	highlight?: boolean | null | undefined
}>()
const { customer, highlight } = toRefs(props)

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

const showDetails = ref(false)
const loading = ref(false)
const router = useRouter()
const message = useMessage()
</script>

<style lang="scss" scoped>
.customer-item {
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

		.toggler-bookmark {
			&.active {
				color: var(--primary-color);
			}
			&:hover {
				color: var(--primary-color);
			}
		}
		.time {
			color: var(--fg-secondary-color);

			&:hover {
				color: var(--primary-color);
			}
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

	&:hover,
	&.highlight {
		box-shadow: 0px 0px 0px 1px inset var(--primary-color);
	}
}
</style>
