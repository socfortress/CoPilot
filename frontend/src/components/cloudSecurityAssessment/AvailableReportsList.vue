<template>
	<div class="available-reports-list">
		<div class="header flex items-center justify-end gap-2 mb-3">
			<div class="info grow flex gap-5">
				<n-popover overlap placement="bottom-start">
					<template #trigger>
						<div class="bg-color border-radius">
							<n-button size="small" class="!cursor-help">
								<template #icon>
									<Icon :name="InfoIcon"></Icon>
								</template>
							</n-button>
						</div>
					</template>
					<div class="flex flex-col gap-2">
						<div class="box">
							Total reports:
							<code>{{ totalReports }}</code>
						</div>
					</div>
				</n-popover>
			</div>
			<div class="actions flex gap-2 items-center">
				<n-button size="small" type="primary">
					<template #icon>
						<Icon :name="NewReportIcon" :size="15"></Icon>
					</template>
					Create new Report
				</n-button>
			</div>
		</div>
		<n-spin :show="loading" class="min-h-32">
			<div class="list grid gap-4 grid-auto-flow-250">
				<template v-if="reportsList.length">
					<AvailableReportsItem
						v-for="report of reportsList"
						:key="report"
						:report
						class="item-appear item-appear-bottom item-appear-005"
						@deleted="getReports()"
					/>
				</template>
				<template v-else>
					<n-empty description="No items found" class="justify-center h-48" v-if="!loading" />
				</template>
			</div>
		</n-spin>
	</div>
</template>
<script setup lang="ts">
import { computed, onBeforeMount, ref } from "vue"
import { NSpin, NEmpty, NPopover, NButton, useMessage } from "naive-ui"
import type { ScoutSuiteReport } from "@/types/cloudSecurityAssessment.d"
import Icon from "@/components/common/Icon.vue"
import AvailableReportsItem from "./AvailableReportsItem.vue"
import Api from "@/api"

const InfoIcon = "carbon:information"
const NewReportIcon = "carbon:fetch-upload-cloud"
const message = useMessage()
const loading = ref(false)
const reportsList = ref<ScoutSuiteReport[]>([])
const totalReports = computed(() => reportsList.value.length)

function getReports() {
	loading.value = true

	Api.cloudSecurityAssessment
		.getAvailableScoutSuiteReports()
		.then(res => {
			if (res.data.success) {
				reportsList.value = res.data?.available_reports || []
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
	getReports()
})
</script>
