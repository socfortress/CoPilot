<template>
	<n-spin :show="loadingAlerts" :size="14">
		<div class="flex alert-list items-center gap-3" v-if="!loadingAlerts">
			<span :class="{ 'text-secondary-color': !alertsList.length, 'font-bold': alertsList.length }">
				{{ alertsList.length || "No Alters" }}
			</span>
			<div class="flex flex-wrap gap-2">
				<n-tooltip v-for="alert of alertsList" :key="alert.alert_id">
					<template #trigger>
						<code class="alert-btn" @click="openSocAlert(alert.alert_id)">#{{ alert.alert_id }}</code>
					</template>
					{{ alert.alert_title }}
				</n-tooltip>
			</div>
		</div>
	</n-spin>

	<n-modal
		v-model:show="showSocAlertDetails"
		preset="card"
		content-class="!p-0"
		:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(250px, 90vh)', overflow: 'hidden' }"
		:title="`SOC Alert: #${selectedAlertId}`"
		:bordered="false"
		segmented
	>
		<div class="h-full w-full flex items-center justify-center">
			<SocAlertItem
				v-if="selectedAlertId"
				:alertId="selectedAlertId"
				embedded
				hideSocCaseAction
				hideBookmarkAction
				class="w-full"
			/>
		</div>
	</n-modal>
</template>

<script setup lang="ts">
import type { SocAlert } from "@/types/soc/alert.d"
import { onBeforeMount, onBeforeUnmount, ref } from "vue"
import Api from "@/api"
import { useMessage, NTooltip, NSpin, NModal } from "naive-ui"
import SocAlertItem from "../SocAlerts/SocAlertItem/SocAlertItem.vue"
import axios from "axios"

const { userId } = defineProps<{
	userId: string | number
}>()

const loadingAlerts = ref(false)
const alertsList = ref<SocAlert[]>([])
const message = useMessage()
let abortController: AbortController | null = null
const showSocAlertDetails = ref(false)
const selectedAlertId = ref<string | number | null>(null)

function openSocAlert(socId: string | number) {
	selectedAlertId.value = socId
	showSocAlertDetails.value = true
}

function getAlerts() {
	loadingAlerts.value = true

	abortController = new AbortController()

	Api.soc
		.getAlertsByUser(userId.toString(), abortController.signal)
		.then(res => {
			if (res.data.success) {
				alertsList.value = res.data?.alerts || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			if (!axios.isCancel(err)) {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			}
		})
		.finally(() => {
			loadingAlerts.value = false
		})
}

onBeforeMount(() => {
	getAlerts()
})

onBeforeUnmount(() => {
	abortController?.abort()
})
</script>

<style lang="scss" scoped>
.alert-list {
	max-width: 200px;
	.alert-btn {
		cursor: pointer;
		text-decoration: underline;

		&:hover {
			color: var(--primary-color);
		}
	}
}
</style>
