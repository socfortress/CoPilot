<template>
	<n-spin :show="loading">
		<!--
		<n-tabs type="line" animated :tabs-padding="24">
			<n-tab-pane name="Overview" tab="Overview" display-directive="show:lazy" class="flex flex-col gap-4 !py-8">
				<div class="px-7">
					<n-card content-class="bg-secondary-color" class="overflow-hidden">
						<div class="flex justify-between gap-8 flex-wrap">
							<n-statistic label="Result" tabular-nums>
								<span
									class="uppercase"
									:class="
										data.result === 'failed'
											? 'text-error-color'
											: data.result === 'not applicable'
												? 'text-warning-color'
												: 'text-success-color'
									"
								>
									{{ data.result }}
								</span>
							</n-statistic>
							<n-statistic label="Condition" tabular-nums>
								<span class="uppercase">{{ data.condition }}</span>
							</n-statistic>
							<n-statistic label="Compliance" :value="data.compliance.length" tabular-nums />
							<n-statistic label="Rules" :value="data.rules.length" tabular-nums />
						</div>
					</n-card>
				</div>

				<div class="px-7">
					<n-card content-class="bg-secondary-color !p-0" class="overflow-hidden">
						<div
							class="scrollbar-styled overflow-hidden code-bg-transparent"
							v-shiki="{ lang: 'shell', decode: true }"
						>
							<pre v-html="data.command"></pre>
						</div>
					</n-card>
				</div>

				<div class="grid gap-2 grid-auto-fit-200 px-7" v-if="properties">
					<KVCard v-for="(value, key) of properties" :key="key">
						<template #key>{{ key }}</template>
						<template #value>{{ value ?? "-" }}</template>
					</KVCard>
				</div>
			</n-tab-pane>
			<n-tab-pane name="Description" tab="Description" display-directive="show:lazy">
				<div class="p-7 pt-4">
					<n-input
						:value="data.description"
						type="textarea"
						readonly
						placeholder="Empty"
						size="large"
						:autosize="{
							minRows: 3,
							maxRows: 18
						}"
					/>
				</div>
			</n-tab-pane>
			<n-tab-pane name="Rationale" tab="Rationale" display-directive="show:lazy">
				<div class="p-7 pt-4">
					<n-input
						:value="data.rationale"
						type="textarea"
						readonly
						placeholder="Empty"
						size="large"
						:autosize="{
							minRows: 3,
							maxRows: 18
						}"
					/>
				</div>
			</n-tab-pane>
			<n-tab-pane name="Reason" tab="Reason" display-directive="show:lazy">
				<div class="p-7 pt-4">
					<n-input
						:value="data.reason"
						type="textarea"
						readonly
						placeholder="Empty"
						size="large"
						:autosize="{
							minRows: 3,
							maxRows: 18
						}"
					/>
				</div>
			</n-tab-pane>
			<n-tab-pane name="Remediation" tab="Remediation" display-directive="show:lazy">
				<div class="p-7 pt-4">
					<n-input
						:value="data.remediation"
						type="textarea"
						readonly
						placeholder="Empty"
						size="large"
						:autosize="{
							minRows: 3,
							maxRows: 18
						}"
					/>
				</div>
			</n-tab-pane>
			<n-tab-pane name="Compliance" tab="Compliance" display-directive="show:lazy">
				<div class="p-7 pt-4 flex flex-col gap-1">
					<n-card
						content-class="bg-secondary-color flex flex-col gap-2"
						class="overflow-hidden"
						size="small"
						v-for="item of data.compliance"
						:key="item.key"
					>
						<div>{{ item.key }}</div>
						<p>{{ item.value }}</p>
					</n-card>
				</div>
			</n-tab-pane>
			<n-tab-pane name="Rules" tab="Rules" display-directive="show:lazy">
				<div class="p-7 pt-4 flex flex-col gap-1">
					<n-card
						content-class="bg-secondary-color flex flex-col gap-2"
						class="overflow-hidden"
						size="small"
						v-for="item of data.rules"
						:key="item.type + item.rule"
					>
						<div>{{ item.type }}</div>
						<p>{{ item.rule }}</p>
					</n-card>
				</div>
			</n-tab-pane>
		</n-tabs>
		-->
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
}>()

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
