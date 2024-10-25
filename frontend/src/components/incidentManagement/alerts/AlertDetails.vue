<template>
	<n-spin :show="loading" class="flex grow flex-col" content-class="flex flex-col grow">
		<n-tabs
			v-if="alert"
			type="line"
			animated
			:tabs-padding="24"
			class="grow"
			pane-wrapper-class="flex flex-col grow"
		>
			<n-tab-pane name="Overview" tab="Overview" display-directive="show:lazy" class="flex grow flex-col">
				<div class="pt-1">
					<AlertOverview :alert @updated="updateAlert($event)" @deleted="emit('deleted')" />
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
					<AlertCommentsList
						:comments="alert.comments"
						:alert-id="alert.id"
						@updated="updateComments($event)"
					/>
				</div>
			</n-tab-pane>
		</n-tabs>
	</n-spin>
</template>

<script setup lang="ts">
import type { Alert, AlertComment } from "@/types/incidentManagement/alerts.d"
import Api from "@/api"
import _clone from "lodash/cloneDeep"
import { NSpin, NTabPane, NTabs, useMessage } from "naive-ui"
import { defineAsyncComponent, onBeforeMount, ref, toRefs } from "vue"

const props = defineProps<{
	alertData?: Alert
	alertId?: number
}>()
const emit = defineEmits<{
	(e: "deleted"): void
	(e: "updated", value: Alert): void
}>()
const AlertTimeline = defineAsyncComponent(() => import("./AlertTimeline.vue"))
const AlertAssetsList = defineAsyncComponent(() => import("./AlertAssetsList.vue"))
const AlertCommentsList = defineAsyncComponent(() => import("./AlertCommentsList.vue"))
const AlertOverview = defineAsyncComponent(() => import("./AlertOverview.vue"))

const { alertData, alertId } = toRefs(props)

const message = useMessage()
const loading = ref(false)
const alert = ref<Alert | null>(null)

function updateAlert(updatedAlert: Alert) {
	alert.value = updatedAlert
	emit("updated", updatedAlert)
}

function updateComments(comments: AlertComment[]) {
	if (alert.value) {
		alert.value.comments = comments
		emit("updated", alert.value)
	}
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
