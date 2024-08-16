<template>
	<n-spin :show="loading" class="flex flex-col grow" content-class="flex flex-col grow">
		<div class="flex flex-col gap-4 grow justify-between">
			<div class="content-box flex flex-col gap-4 py-3">
				<div class="px-7 flex sm:!flex-row flex-col gap-4">
					<KVCard
						:color="
							alert.status === 'OPEN' ? 'danger' : alert.status === 'IN_PROGRESS' ? 'warning' : 'success'
						"
						size="lg"
						class="grow w-full"
					>
						<template #key>
							<div class="flex gap-2 items-center">
								<StatusIcon :status="alert.status" />
								<span>Status</span>
							</div>
						</template>
						<template #value>
							<div class="flex">
								<AlertStatusSwitch
									:alert
									v-slot="{ loading: loadingStatus }"
									@updated="updateAlert($event)"
								>
									<div
										class="flex gap-3 items-center"
										:class="{
											'cursor-not-allowed': loadingStatus,
											'cursor-pointer': !loadingStatus
										}"
									>
										<span>{{ alert.status || "n/d" }}</span>
										<n-spin
											:size="14"
											:show="loadingStatus"
											content-class="flex flex-col justify-center"
										>
											<Icon :name="EditIcon" />
										</n-spin>
									</div>
								</AlertStatusSwitch>
							</div>
						</template>
					</KVCard>

					<KVCard :color="alert.assigned_to ? 'success' : undefined" size="lg" class="grow w-full">
						<template #key>
							<div class="flex gap-2 items-center">
								<AssigneeIcon :assignee="alert.assigned_to" />
								<span>Assigned to</span>
							</div>
						</template>
						<template #value>
							<div class="flex">
								<AlertAssignUser
									:alert
									:users="availableUsers"
									v-slot="{ loading: loadingAssignee }"
									@updated="updateAlert($event)"
								>
									<div
										class="flex gap-3 items-center"
										:class="{
											'cursor-not-allowed': loadingAssignee,
											'cursor-pointer': !loadingAssignee
										}"
									>
										<span>{{ alert.assigned_to || "n/d" }}</span>
										<n-spin
											:size="14"
											:show="loadingAssignee"
											content-class="flex flex-col justify-center"
										>
											<Icon :name="EditIcon" />
										</n-spin>
									</div>
								</AlertAssignUser>
							</div>
						</template>
					</KVCard>
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
						<template #value>
							<div class="flex flex-wrap gap-2">
								<n-tag
									closable
									@close="deleteTag(tag)"
									v-for="{ tag } of alert.tags"
									:key="tag"
									size="small"
								>
									{{ tag }}
								</n-tag>
							</div>
						</template>
					</KVCard>
				</div>
			</div>

			<div class="footer-box px-7 py-4 flex justify-between">
				<n-button secondary @click="createCase()" v-if="!hideCreateCaseButton">
					<template #icon><Icon :name="DangerIcon" /></template>
					Create case
				</n-button>
				<n-button type="error" secondary @click="handleDelete()">
					<template #icon><Icon :name="TrashIcon" /></template>
					Delete
				</n-button>
			</div>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import { ref, toRefs } from "vue"
import { NButton, NSpin, NTag, useMessage, useDialog } from "naive-ui"
import AlertAssignUser from "./AlertAssignUser.vue"
import AlertStatusSwitch from "./AlertStatusSwitch.vue"
import StatusIcon from "../common/StatusIcon.vue"
import AssigneeIcon from "../common/AssigneeIcon.vue"
import KVCard from "@/components/common/KVCard.vue"
import Icon from "@/components/common/Icon.vue"
import { useGoto } from "@/composables/useGoto"
import { handleDeleteAlert } from "./utils"
import Api from "@/api"
import type { Alert } from "@/types/incidentManagement/alerts.d"

const props = defineProps<{ alert: Alert; availableUsers?: string[]; hideCreateCaseButton?: boolean }>()
const { alert, availableUsers, hideCreateCaseButton } = toRefs(props)

const emit = defineEmits<{
	(e: "deleted"): void
	(e: "updated", value: Alert): void
}>()

const TrashIcon = "carbon:trash-can"
const LinkIcon = "carbon:launch"
const DangerIcon = "majesticons:exclamation-line"
const EditIcon = "uil:edit-alt"

const { gotoCustomer } = useGoto()
const dialog = useDialog()
const message = useMessage()
const loading = ref(false)

function updateAlert(updatedAlert: Alert) {
	emit("updated", updatedAlert)
}

function createCase() {
	// TODO: to implement
}

function handleDelete() {
	if (alert.value) {
		handleDeleteAlert({
			alert: alert.value,
			cbBefore: () => {
				loading.value = true
			},
			cbSuccess: () => {
				emit("deleted")
			},
			cbAfter: () => {
				loading.value = false
			},
			message,
			dialog
		})
	}
}

function deleteTag(tag: string) {
	loading.value = true

	Api.incidentManagement
		.deleteAlertTag(alert.value.id, tag)
		.then(res => {
			if (res.data.success) {
				message.success("Alert tag was successfully deleted.")

				alert.value.tags = alert.value.tags.filter(o => o.tag !== tag)
				updateAlert(alert.value)
			} else {
				message.error(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			if (err.response?.status === 401) {
				message.error(err.response?.data?.message || "Alert tag Delete returned Unauthorized.")
			} else {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			}
		})
		.finally(() => {
			loading.value = false
		})
}
</script>

<style lang="scss" scoped>
.footer-box {
	border-top: var(--border-small-100);
	background-color: var(--bg-secondary-color);
}
</style>
