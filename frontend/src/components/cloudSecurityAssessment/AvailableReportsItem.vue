<template>
	<n-spin :show="canceling">
		<div class="item flex flex-col gap-2 px-5 py-3" @click="openReport()">
			<div class="header-box flex justify-between">
				{{ report }}
			</div>
			<div class="footer-box flex justify-end">
				<n-popconfirm
					v-model:show="showConfirm"
					trigger="manual"
					@positive-click="deleteScoutSuiteReport()"
					@clickoutside="showConfirm = false"
				>
					<template #trigger>
						<div class="delete-btn" @click.stop="showConfirm = true">
							delete
						</div>
					</template>
					Are you sure you want to delete the report?
				</n-popconfirm>
			</div>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { ScoutSuiteReport } from "@/types/cloudSecurityAssessment.d"
import Api from "@/api"
import { getBaseUrl } from "@/utils"
import { NPopconfirm, NSpin, useMessage } from "naive-ui"
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

<style lang="scss" scoped>
.item {
	border-radius: var(--border-radius);
	background-color: var(--bg-color);
	transition: all 0.2s var(--bezier-ease);
	border: var(--border-small-050);
	cursor: pointer;

	.header-box {
		font-family: var(--font-family-mono);
	}
	.footer-box {
		font-family: var(--font-family-mono);
		text-align: right;
		font-size: 12px;
		color: var(--fg-secondary-color);

		.delete-btn {
			&:hover {
				color: var(--error-color);
			}
		}
	}

	&:hover {
		box-shadow: 0px 0px 0px 1px inset var(--primary-color);
	}
}
</style>
