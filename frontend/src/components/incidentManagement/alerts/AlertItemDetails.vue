<template>
	<n-spin :show="loading" class="flex flex-col grow" content-class="flex flex-col grow">
		<n-tabs
			type="line"
			animated
			:tabs-padding="24"
			v-if="alert"
			class="grow"
			pane-wrapper-class="flex flex-col grow"
		>
			<n-tab-pane name="Overview" tab="Overview" display-directive="show:lazy" class="flex flex-col grow">
				<div class="pt-1">
					<AlertItemOverview :alert :availableUsers @update="updateAlert($event)" @delete="emit('delete')" />
				</div>
			</n-tab-pane>
			<n-tab-pane name="Timeline" tab="Timeline" display-directive="show:lazy">
				<div class="p-7 pt-4">
					<AlertTimeline :alert />
				</div>
			</n-tab-pane>
			<n-tab-pane name="Assets" tab="Assets" display-directive="show:lazy">
				<div class="p-7 pt-4">
					<AlertAssetsList :assets="alert.assets" />
				</div>
			</n-tab-pane>
			<n-tab-pane name="Comments" tab="Comments" display-directive="show:lazy">
				<div class="p-7 pt-4">
					<AlertCommentsList :comments="alert.comments" />
				</div>
			</n-tab-pane>
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
import AlertAssetsList from "./AlertAssetsList.vue"
import AlertCommentsList from "./AlertAssetsList.vue"
import AlertItemOverview from "./AlertItemOverview.vue"
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
const DangerIcon = "majesticons:exclamation-line"
const EditIcon = "uil:edit-alt"
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

onBeforeMount(() => {
	if (alertId.value) {
		getAlert(alertId.value)
	} else if (alertData.value) {
		alert.value = _clone(alertData.value)
	}
})
</script>
