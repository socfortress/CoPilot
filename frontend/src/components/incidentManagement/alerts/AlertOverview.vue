<template>
	<n-spin :show="loading" class="flex grow flex-col" content-class="flex flex-col grow">
		<div class="flex grow flex-col justify-between gap-4">
			<div class="content-box flex flex-col gap-4 py-3">
				<div class="flex flex-col gap-4 px-7 sm:!flex-row">
					<KVCard
						:color="
							alert.status === 'OPEN' ? 'danger' : alert.status === 'IN_PROGRESS' ? 'warning' : 'success'
						"
						size="lg"
						class="w-full grow"
					>
						<template #key>
							<div class="flex items-center gap-2">
								<StatusIcon :status="alert.status" />
								<span>Status</span>
							</div>
						</template>
						<template #value>
							<div class="flex">
								<AlertStatusSwitch
									v-slot="{ loading: loadingStatus }"
									:alert
									@updated="updateAlert($event)"
								>
									<div
										class="flex items-center gap-3"
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

					<KVCard :color="alert.assigned_to ? 'success' : undefined" size="lg" class="w-full grow">
						<template #key>
							<div class="flex items-center gap-2">
								<AssigneeIcon :assignee="alert.assigned_to" />
								<span>Assigned to</span>
							</div>
						</template>
						<template #value>
							<div class="flex">
								<AlertAssignUser
									v-slot="{ loading: loadingAssignee }"
									:alert
									@updated="updateAlert($event)"
								>
									<div
										class="flex items-center gap-3"
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
						<template #value>
							{{ alert.alert_description ?? "-" }}
						</template>
					</KVCard>
				</div>

				<div class="grid-auto-fit-250 grid gap-2 px-7">
					<KVCard>
						<template #key>id</template>
						<template #value>#{{ alert.id }}</template>
					</KVCard>

					<KVCard>
						<template #key>source</template>
						<template #value>
							{{ alert.source ?? "-" }}
						</template>
					</KVCard>

					<KVCard>
						<template #key>customer code</template>
						<template #value>
							<code
								class="text-primary cursor-pointer"
								@click="gotoCustomer({ code: alert.customer_code })"
							>
								{{ alert.customer_code }}
								<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
							</code>
						</template>
					</KVCard>

					<KVCard>
						<template #key>assets</template>
						<template #value>
							{{ alert.assets.length }}
						</template>
					</KVCard>

					<KVCard>
						<template #key>comments</template>
						<template #value>
							{{ alert.comments.length }}
						</template>
					</KVCard>

					<KVCard>
						<template #key>tags</template>
						<template #value>
							<AlertTags :alert @updated="updateAlert" />
						</template>
					</KVCard>
				</div>
			</div>

			<div class="footer-box flex items-center gap-2 px-7 py-4">
				<AlertCreateCaseButton v-if="!linkedCases.length" :alert @updated="updateAlert" />

				<AlertMergeCaseButton v-if="!linkedCases.length" :alert @updated="updateAlert" />

				<div v-if="linkedCases.length" class="flex flex-wrap items-center gap-3">
					<span>Linked Cases:</span>
					<AlertLinkedCases :alert />
				</div>

				<div class="grow"></div>

				<n-button type="error" secondary @click="handleDelete()">
					<template #icon>
						<Icon :name="TrashIcon" />
					</template>
					Delete
				</n-button>
			</div>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { Alert } from "@/types/incidentManagement/alerts.d"
import Icon from "@/components/common/Icon.vue"
import KVCard from "@/components/common/KVCard.vue"
import { useGoto } from "@/composables/useGoto"
import { NButton, NSpin, useDialog, useMessage } from "naive-ui"
import { computed, defineAsyncComponent, ref, toRefs } from "vue"
import AssigneeIcon from "../common/AssigneeIcon.vue"
import StatusIcon from "../common/StatusIcon.vue"
import AlertAssignUser from "./AlertAssignUser.vue"
import AlertStatusSwitch from "./AlertStatusSwitch.vue"
import AlertTags from "./AlertTags.vue"
import { handleDeleteAlert } from "./utils"

const props = defineProps<{ alert: Alert }>()
const emit = defineEmits<{
	(e: "deleted"): void
	(e: "updated", value: Alert): void
}>()
const AlertCreateCaseButton = defineAsyncComponent(() => import("./AlertCreateCaseButton.vue"))
const AlertMergeCaseButton = defineAsyncComponent(() => import("./AlertMergeCaseButton.vue"))
const AlertLinkedCases = defineAsyncComponent(() => import("./AlertLinkedCases.vue"))

const { alert } = toRefs(props)

const TrashIcon = "carbon:trash-can"
const LinkIcon = "carbon:launch"
const EditIcon = "uil:edit-alt"

const { gotoCustomer } = useGoto()
const dialog = useDialog()
const message = useMessage()
const loading = ref(false)
const linkedCases = computed(() => alert.value.linked_cases)

function updateAlert(updatedAlert: Alert) {
	emit("updated", updatedAlert)
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
</script>

<style lang="scss" scoped>
.footer-box {
	border-top: var(--border-small-100);
	background-color: var(--bg-secondary-color);
}
</style>
