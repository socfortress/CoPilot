<template>
	<n-spin :show="loading">
		<n-tabs type="line" animated :tabs-padding="24" v-if="alert">
			<n-tab-pane name="Overview" tab="Overview" display-directive="show:lazy" class="flex flex-col gap-4 !pt-4">
				<div class="px-7 flex sm:flex-row flex-col gap-4">
					<n-card content-class="bg-secondary-color" class="overflow-hidden">
						<div class="flex justify-between gap-8 flex-wrap">
							<n-statistic label="Status">
								<AlertStatusSwitch
									:alert
									v-slot="{ loading: loadingStatus }"
									@updated="updateAlert($event)"
								>
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
											<n-spin
												:size="12"
												:show="loadingStatus"
												content-class="flex flex-col justify-center"
											>
												<AlertStatusIcon :status="alert.status" />
											</n-spin>
										</template>
										<template #label>Status</template>
										<template #value>{{ alert.status || "n/d" }}</template>
									</Badge>
								</AlertStatusSwitch>
							</n-statistic>
						</div>
					</n-card>
					<n-card content-class="bg-secondary-color" class="overflow-hidden">
						<div class="flex justify-between gap-8 flex-wrap">
							<n-statistic label="Assigned to">
								<AlertAssignUser
									:alert
									:users="availableUsers"
									v-slot="{ loading: loadingAssignee }"
									@updated="updateAlert($event)"
								>
									<Badge
										type="splitted"
										class="cursor-pointer"
										bright
										:color="alert.assigned_to ? 'success' : undefined"
									>
										<template #iconLeft>
											<n-spin
												:size="12"
												:show="loadingAssignee"
												content-class="flex flex-col justify-center"
											>
												<AlertAssigneeIcon :assignee="alert.assigned_to" />
											</n-spin>
										</template>
										<template #label>Assignee</template>
										<template #value>{{ alert.assigned_to || "n/d" }}</template>
									</Badge>
								</AlertAssignUser>
							</n-statistic>
						</div>
					</n-card>
				</div>

				<div class="px-7">
					<KVCard>
						<template #key>description</template>
						<template #value>{{ alert.alert_description ?? "-" }}</template>
					</KVCard>
				</div>

				<div class="px-7 grid gap-2 grid-auto-fit-250">
					<KVCard>
						<template #key>id</template>
						<template #value>#{{ alert.id }}</template>
					</KVCard>

					<KVCard>
						<template #key>source</template>
						<template #value>{{ alert.source ?? "-" }}</template>
					</KVCard>

					<KVCard>
						<template #key>customer code</template>
						<template #value>
							<code
								class="cursor-pointer text-primary-color"
								@click="gotoCustomer({ code: alert.customer_code })"
							>
								{{ alert.customer_code }}
								<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
							</code>
						</template>
					</KVCard>

					<KVCard>
						<template #key>assets</template>
						<template #value>{{ alert.assets.length }}</template>
					</KVCard>

					<KVCard>
						<template #key>comments</template>
						<template #value>{{ alert.comments.length }}</template>
					</KVCard>

					<KVCard>
						<template #key>tags</template>
						<template #value>{{ tags || "-" }}</template>
					</KVCard>
				</div>

				<div class="px-7 py-4 flex justify-between actions-box">
					<n-button secondary :loading @click="createCase()">
						<template #icon><Icon :name="TrashIcon" /></template>
						Create case
					</n-button>
					<n-button type="error" secondary :loading @click="handleDelete()">
						<template #icon><Icon :name="TrashIcon" /></template>
						Delete
					</n-button>
				</div>
			</n-tab-pane>
			<n-tab-pane name="Timeline" tab="Timeline" display-directive="show:lazy">
				<div class="p-7 pt-4">
					<AlertTimeline :alert />
				</div>
			</n-tab-pane>
			<n-tab-pane name="Assets" tab="Assets" display-directive="show:lazy"></n-tab-pane>
			<n-tab-pane name="Comments" tab="Comments" display-directive="show:lazy"></n-tab-pane>
			<n-tab-pane name="Tags" tab="Tags" display-directive="show:lazy"></n-tab-pane>
		</n-tabs>
	</n-spin>
</template>

<script setup lang="ts">
import { onBeforeMount, ref, toRefs, computed } from "vue"
import {
	NTabs,
	NTabPane,
	NStatistic,
	NInput,
	NCard,
	NModal,
	NPopover,
	NButton,
	NSpin,
	useMessage,
	useDialog
} from "naive-ui"
import KVCard from "@/components/common/KVCard.vue"
import { useSettingsStore } from "@/stores/settings"
import { useGoto } from "@/composables/useGoto"
import { formatDate } from "@/utils"
import _clone from "lodash/cloneDeep"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import Badge from "@/components/common/Badge.vue"
import AlertTimeline from "./AlertTimeline.vue"
import AlertAssignUser from "./AlertAssignUser.vue"
import AlertStatusSwitch from "./AlertStatusSwitch.vue"
import AlertStatusIcon from "./AlertStatusIcon.vue"
import AlertAssigneeIcon from "./AlertAssigneeIcon.vue"
import AlertItemDetails from "./AlertItemDetails.vue"
import { handleDeleteAlert } from "./utils"
import type { Alert } from "@/types/incidentManagement/alerts.d"

const props = defineProps<{ alertData?: Alert; alertId?: number; availableUsers?: string[] }>()
const { alertData, alertId, availableUsers } = toRefs(props)

const emit = defineEmits<{
	(e: "delete"): void
	(e: "update", value: Alert): void
}>()

const TrashIcon = "carbon:trash-can"
const InfoIcon = "carbon:information"
const LinkIcon = "carbon:launch"
const TimeIcon = "carbon:time"
const CommentsIcon = "carbon:chat"
const AssetsIcon = "carbon:document-security"

const { gotoCustomer } = useGoto()
const dialog = useDialog()
const message = useMessage()
const loading = ref(false)
const dFormats = useSettingsStore().dateFormat
const alert = ref<Alert | null>(null)

const tags = computed(() => (alert.value?.tags?.length ? alert.value.tags.map(o => "#" + o.tag).join(", ") : ""))

function updateAlert(updatedAlert: Alert) {
	alert.value = updatedAlert
	emit("update", updatedAlert)
}

function createCase() {
	// TODO: to implement
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
				emit("delete")
			},
			cbAfter: () => {
				loading.value = false
			},
			message,
			dialog
		})
	}
}

onBeforeMount(() => {
	if (alertId.value) {
		getAlert(alertId.value)
	} else if (alertData.value) {
		alert.value = _clone(alertData.value)
	}
})
</script>

<style lang="scss" scoped>
.actions-box {
	border-top: var(--border-small-100);
	background-color: var(--bg-secondary-color);
}
</style>
