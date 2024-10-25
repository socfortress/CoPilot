<template>
	<CardEntity :loading="canceling" hoverable clickable @click.stop="openReport()">
		<template #default>
			{{ report }}
		</template>
		<template #footerExtra>
			<n-popconfirm
				v-model:show="showConfirm"
				trigger="manual"
				@positive-click="deleteScoutSuiteReport()"
				@clickoutside="showConfirm = false"
			>
				<template #trigger>
					<n-button quaternary size="tiny" @click.stop="showConfirm = true">delete</n-button>
				</template>
				Are you sure you want to delete the report?
			</n-popconfirm>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { ScoutSuiteReport } from "@/types/cloudSecurityAssessment.d"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import { getBaseUrl } from "@/utils"
import { NButton, NPopconfirm, useMessage } from "naive-ui"
import { ref } from "vue"

const { report } = defineProps<{ report: ScoutSuiteReport }>()

const emit = defineEmits<{
	(e: "deleted"): void
}>()

const message = useMessage()
const canceling = ref(false)
const showConfirm = ref(false)

function deleteScoutSuiteReport() {
	canceling.value = true

	Api.cloudSecurityAssessment
		.deleteScoutSuiteReport(report)
		.then(res => {
			if (res.data.success) {
				message.success(res.data?.message || "Report deleted successfully")
				emit("deleted")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			canceling.value = false
		})
}

function openReport() {
	window.open(`${getBaseUrl()}/scoutsuite-report/${report}`, "_blank")
}
</script>
