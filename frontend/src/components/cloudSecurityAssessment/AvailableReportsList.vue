<template>
	<div class="available-reports-list">
		<div class="header mb-3 flex items-center justify-end gap-2">
			<div class="info flex grow gap-5">
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
			<div class="actions flex items-center gap-2">
				<n-button size="small" type="primary" @click="showForm = true">
					<template #icon>
						<Icon :name="NewReportIcon" :size="15"></Icon>
					</template>
					Create new Report
				</n-button>
			</div>
		</div>
		<n-spin :show="loading" class="min-h-32">
			<template v-if="reportsList.length">
				<div class="list grid-auto-fill-250 grid gap-4">
					<AvailableReportsItem
						v-for="report of reportsList"
						:key="report"
						:report
						class="item-appear item-appear-bottom item-appear-005"
						@deleted="getReports()"
					/>
				</div>
			</template>
			<template v-else>
				<n-empty v-if="!loading" description="No items found" class="h-48 justify-center" />
			</template>
		</n-spin>

		<n-modal
			v-model:show="showForm"
			display-directive="show"
			preset="card"
			:style="{ maxWidth: 'min(600px, 90vw)', minHeight: 'min(270px, 90vh)', overflow: 'hidden' }"
			title="Generate Report"
			:bordered="false"
			segmented
		>
			<CreationReportForm @submitted="getReports()" @mounted="formCTX = $event" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { ScoutSuiteReport } from "@/types/cloudSecurityAssessment.d"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { NButton, NEmpty, NModal, NPopover, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import AvailableReportsItem from "./AvailableReportsItem.vue"
import CreationReportForm from "./CreationReportForm.vue"

const InfoIcon = "carbon:information"
const NewReportIcon = "carbon:fetch-upload-cloud"
const message = useMessage()
const showForm = ref(false)
const loading = ref(false)
const reportsList = ref<ScoutSuiteReport[]>([])
const totalReports = computed(() => reportsList.value.length)
const formCTX = ref<{ reset: () => void } | null>(null)

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

watch(showForm, val => {
	if (val) {
		formCTX.value?.reset()
	}
})

onBeforeMount(() => {
	getReports()
})
</script>
