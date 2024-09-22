<template>
	<n-spin :show="canceling">
		<div class="item flex flex-col gap-2 px-5 py-3" @click="openConfiguredSource()">
			<div class="header-box flex justify-between">
				{{ source }}
			</div>
			<div class="footer-box flex justify-end">
				<n-popconfirm
					v-model:show="showConfirm"
					trigger="manual"
					@positive-click="deleteSourceConfiguration()"
					@clickoutside="showConfirm = false"
				>
					<template #trigger>
						<div class="delete-btn" @click.stop="showConfirm = true">delete</div>
					</template>
					Are you sure you want to delete the source configuration?
				</n-popconfirm>
			</div>
		</div>

		<n-modal
			v-model:show="showDetails"
			display-directive="show"
			preset="card"
			:style="{ maxWidth: 'min(600px, 90vw)', minHeight: 'min(300px, 90vh)', overflow: 'hidden' }"
			:title="source"
			:bordered="false"
			segmented
		>
			<SourceConfigurationDetails :source />
		</n-modal>
	</n-spin>
</template>

<script setup lang="ts">
import type { SourceName } from "@/types/incidentManagement/sources.d"
import Api from "@/api"
import { NModal, NPopconfirm, NSpin, useMessage } from "naive-ui"
import { ref } from "vue"
import SourceConfigurationDetails from "./SourceConfigurationDetails.vue"

const { source } = defineProps<{ source: SourceName }>()

const emit = defineEmits<{
	(e: "deleted"): void
}>()

const message = useMessage()
const canceling = ref(false)
const showDetails = ref(false)
const showConfirm = ref(false)

function deleteSourceConfiguration() {
	canceling.value = true

	Api.incidentManagement
		.deleteSourceConfiguration(source)
		.then(res => {
			if (res.data.success) {
				message.success(res.data?.message || "Source Configuration deleted successfully")
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

function openConfiguredSource() {
	showDetails.value = true
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
