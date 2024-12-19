<template>
	<div>
		<CardEntity
			:loading
			:embedded
			hoverable
			:size="compact ? 'small' : 'medium'"
			:clickable="compact"
			:highlighted="highlight"
			@click="compact ? openDetails() : undefined"
		>
			<template v-if="alert" #headerMain>
				<div class="flex items-center gap-4">
					<div v-if="selectable">
						<n-checkbox :checked="checked" @click.stop="emit('check', !checked)" />
					</div>
					<div
						class="flex cursor-pointer items-center gap-2"
						:class="{ 'hover:text-primary cursor-pointer': !compact }"
						@click="compact ? undefined : openDetails()"
					>
						<span>#{{ alert.id }} - {{ alert.source }}</span>
						<Icon v-if="!compact" :name="InfoIcon" :size="16"></Icon>
					</div>
				</div>
			</template>

			<template v-if="alert?.alert_creation_time" #headerExtra>
				<div :class="{ 'hidden sm:block': !compact }">
					<n-popover
						v-if="!compact"
						overlap
						placement="top-end"
						style="max-height: 240px"
						scrollable
						to="body"
					>
						<template #trigger>
							<div class="flex cursor-help items-center gap-2">
								<span v-if="alert.alert_creation_time">
									{{ formatDate(alert.alert_creation_time, dFormats.datetime) }}
								</span>
								<Icon :name="TimeIcon" :size="16"></Icon>
							</div>
						</template>
						<div class="flex flex-col px-1 py-2">
							<AlertTimeline v-if="alert" :alert />
						</div>
					</n-popover>
					<span v-if="compact && alert.alert_creation_time">
						{{ formatDate(alert.alert_creation_time, dFormats.datetime) }}
					</span>
				</div>
			</template>

			<template v-if="alert" #default>
				{{ alert.alert_name }}
			</template>

			<template v-if="alert" #mainExtra>
				<div v-if="compact" class="flex flex-wrap items-center gap-3">
					<Badge
						type="splitted"
						class="cursor-pointer"
						bright
						:color="
							alert.status === 'OPEN' ? 'danger' : alert.status === 'IN_PROGRESS' ? 'warning' : 'success'
						"
					>
						<template #iconLeft>
							<StatusIcon :status="alert.status" />
						</template>
						<template #label>Status</template>
						<template #value>
							<div class="flex items-center gap-2">
								{{ alert.status || "n/d" }}
							</div>
						</template>
					</Badge>

					<Badge
						type="splitted"
						class="cursor-pointer"
						bright
						:color="alert.assigned_to ? 'success' : undefined"
					>
						<template #iconLeft>
							<AssigneeIcon :assignee="alert.assigned_to" />
						</template>
						<template #label>Assignee</template>
						<template #value>
							<div class="flex items-center gap-2">
								{{ alert.assigned_to || "n/d" }}
							</div>
						</template>
					</Badge>
				</div>
				<div v-else class="flex flex-wrap items-center gap-3">
					<AlertStatusSwitch v-slot="{ loading: loadingStatus }" :alert @updated="updateAlert($event)">
						<Badge
							type="splitted"
							class="cursor-pointer"
							bright
							:color="
								alert.status === 'OPEN'
									? 'danger'
									: alert.status === 'IN_PROGRESS'
										? 'warning'
										: 'success'
							"
						>
							<template #iconLeft>
								<n-spin :size="12" :show="loadingStatus" content-class="flex flex-col justify-center">
									<StatusIcon :status="alert.status" />
								</n-spin>
							</template>
							<template #label>Status</template>
							<template #value>
								<div class="flex items-center gap-2">
									{{ alert.status || "n/d" }}
									<Icon :name="EditIcon" :size="13" />
								</div>
							</template>
						</Badge>
					</AlertStatusSwitch>

					<AlertAssignUser v-slot="{ loading: loadingAssignee }" :alert @updated="updateAlert($event)">
						<Badge
							type="splitted"
							class="cursor-pointer"
							bright
							:color="alert.assigned_to ? 'success' : undefined"
						>
							<template #iconLeft>
								<n-spin :size="12" :show="loadingAssignee" content-class="flex flex-col justify-center">
									<AssigneeIcon :assignee="alert.assigned_to" />
								</n-spin>
							</template>
							<template #label>Assignee</template>
							<template #value>
								<div class="flex items-center gap-2">
									{{ alert.assigned_to || "n/d" }}
									<Icon :name="EditIcon" :size="13" />
								</div>
							</template>
						</Badge>
					</AlertAssignUser>

					<Badge v-if="alert.customer_code" type="splitted" class="!hidden sm:!flex">
						<template #label>Customer</template>
						<template #value>
							<div class="flex h-full items-center">
								<code
									class="text-primary cursor-pointer leading-none"
									@click.stop="gotoCustomer({ code: alert.customer_code })"
								>
									#{{ alert.customer_code }}
									<Icon :name="LinkIcon" :size="14" class="relative top-0.5" />
								</code>
							</div>
						</template>
					</Badge>

					<Badge v-if="alert.assets?.length" type="splitted" fluid class="!hidden sm:!flex">
						<template #label>Assets</template>
						<template #value>
							<div class="flex flex-wrap gap-1">
								<AlertAssetItem v-for="asset of alert.assets" :key="asset.id" :asset badge />
							</div>
						</template>
					</Badge>

					<Badge type="splitted" class="!hidden sm:!flex">
						<template #label>Linked Cases</template>
						<template #value>
							<AlertLinkedCases v-if="alert.linked_cases?.length" :alert />
							<span v-else>n/d</span>
						</template>
					</Badge>
				</div>
			</template>

			<template v-if="alert && !compact" #footerMain>
				<div class="flex items-center gap-3">
					<Badge v-if="alert.alert_creation_time" type="splitted" :class="{ 'flex sm:!hidden': !compact }">
						<template #iconLeft>
							<Icon :name="TimeIcon" :size="16" />
						</template>
						<template #value>
							{{ formatDate(alert.alert_creation_time, dFormats.datetime) }}
						</template>
					</Badge>

					<n-tooltip trigger="hover">
						<template #trigger>
							<Badge type="splitted" class="xs:!flex !hidden">
								<template #iconLeft>
									<Icon :name="AssetsIcon" :size="16" />
								</template>
								<template #value>
									{{ alert.assets?.length || 0 }}
								</template>
							</Badge>
						</template>
						Assets
					</n-tooltip>

					<n-tooltip trigger="hover">
						<template #trigger>
							<Badge type="splitted" class="xs:!flex !hidden">
								<template #iconLeft>
									<Icon :name="CommentsIcon" :size="16" />
								</template>
								<template #value>
									{{ alert.comments?.length || 0 }}
								</template>
							</Badge>
						</template>
						Comments
					</n-tooltip>

					<n-tooltip trigger="hover">
						<template #trigger>
							<Badge type="splitted" class="xs:!flex !hidden">
								<template #iconLeft>
									<Icon :name="IoCsIcon" :size="16" />
								</template>
								<template #value>
									{{ alert.iocs?.length || 0 }}
								</template>
							</Badge>
						</template>
						IoC
					</n-tooltip>

					<span
						v-for="tag of alert.tags"
						:key="tag.tag"
						class="text-secondary"
						:class="{ 'hidden sm:inline-block': !compact }"
					>
						#{{ tag.tag }}
					</span>
				</div>
			</template>

			<template v-if="alert && !compact" #footerExtra>
				<n-button quaternary size="tiny" @click.stop="handleDelete()">Delete</n-button>
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showDetails"
			:style="{ maxWidth: 'min(850px, 90vw)', minHeight: 'min(540px, 90vh)', overflow: 'hidden' }"
			display-directive="show"
		>
			<n-card
				content-class="flex flex-col !p-0"
				:title="alertNameTruncated"
				closable
				:bordered="false"
				segmented
				role="modal"
				@close="closeDetails()"
			>
				<AlertDetails v-if="alert" :alert-data="alert" @deleted="emitDelete()" @updated="updateAlert($event)" />
			</n-card>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { Alert } from "@/types/incidentManagement/alerts.d"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useGoto } from "@/composables/useGoto"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import _clone from "lodash/cloneDeep"
import _truncate from "lodash/truncate"
import { NButton, NCard, NCheckbox, NModal, NPopover, NSpin, NTooltip, useDialog, useMessage } from "naive-ui"
import { computed, defineAsyncComponent, onBeforeMount, onMounted, ref, toRefs, watch } from "vue"
import AssigneeIcon from "../common/AssigneeIcon.vue"
import StatusIcon from "../common/StatusIcon.vue"
import AlertAssignUser from "./AlertAssignUser.vue"
import AlertDetails from "./AlertDetails.vue"
import AlertStatusSwitch from "./AlertStatusSwitch.vue"
import AlertTimeline from "./AlertTimeline.vue"
import { handleDeleteAlert } from "./utils"

const props = defineProps<{
	alertData?: Alert
	alertId?: number
	compact?: boolean
	embedded?: boolean
	detailsOnMounted?: boolean
	highlight?: boolean
	selectable?: boolean
	checked?: boolean
}>()

const emit = defineEmits<{
	(e: "check", value: boolean): void
	(e: "opened"): void
	(e: "deleted"): void
	(e: "updated", value: Alert): void
}>()

const AlertAssetItem = defineAsyncComponent(() => import("./AlertAsset.vue"))
const AlertLinkedCases = defineAsyncComponent(() => import("./AlertLinkedCases.vue"))

const { alertData, alertId, compact, embedded, detailsOnMounted, highlight, selectable, checked } = toRefs(props)

const InfoIcon = "carbon:information"
const LinkIcon = "carbon:launch"
const TimeIcon = "carbon:time"
const EditIcon = "uil:edit-alt"
const CommentsIcon = "carbon:chat"
const AssetsIcon = "carbon:document-security"
const IoCsIcon = "carbon:ibm-watson-discovery"

const { gotoCustomer } = useGoto()
const dialog = useDialog()
const message = useMessage()
const loading = ref(false)
const showDetails = ref(false)
const dFormats = useSettingsStore().dateFormat
const alert = ref<Alert | null>(null)
const alertNameTruncated = computed(() => _truncate(alert.value?.alert_name, { length: 50 }))

function updateAlert(updatedAlert: Alert) {
	alert.value = updatedAlert
	emit("updated", updatedAlert)
}

function getAlert(alertId: number) {
	loading.value = true

	Api.incidentManagement
		.getAlert(alertId)
		.then(res => {
			if (res.data.success) {
				alert.value = res.data?.alerts?.[0] || null
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

function handleDelete() {
	if (alert.value) {
		handleDeleteAlert({
			alert: alert.value,
			cbBefore: () => {
				loading.value = true
			},
			cbSuccess: () => {
				emitDelete()
			},
			cbAfter: () => {
				loading.value = false
			},
			message,
			dialog
		})
	}
}

function emitDelete() {
	showDetails.value = false
	emit("deleted")
}

function openDetails() {
	emit("opened")
	showDetails.value = true
}

function closeDetails() {
	showDetails.value = false
}

watch(
	[alertId, alertData],
	() => {
		if (alertId.value) {
			getAlert(alertId.value)
		} else if (alertData.value?.id && alertData.value?.linked_cases === undefined) {
			getAlert(alertData.value.id)
		} else if (alertData.value) {
			alert.value = _clone(alertData.value)
		}
	},
	{ immediate: true }
)

onMounted(() => {
	if (detailsOnMounted.value) {
		openDetails()
	}
})
</script>
