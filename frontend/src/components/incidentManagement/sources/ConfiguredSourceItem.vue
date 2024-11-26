<template>
	<div>
		<CardEntity :loading="canceling" hoverable clickable @click.stop="openConfiguredSource()">
			<template #default>
				{{ source }}
			</template>
			<template #footerExtra>
				<n-popconfirm
					v-model:show="showConfirm"
					trigger="manual"
					@positive-click="deleteSourceConfiguration()"
					@clickoutside="showConfirm = false"
				>
					<template #trigger>
						<n-button quaternary size="tiny" @click.stop="showConfirm = true">delete</n-button>
					</template>
					Are you sure you want to delete the source configuration?
				</n-popconfirm>
			</template>
		</CardEntity>

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
	</div>
</template>

<script setup lang="ts">
import type { SourceName } from "@/types/incidentManagement/sources.d"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import { NButton, NModal, NPopconfirm, useMessage } from "naive-ui"
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
