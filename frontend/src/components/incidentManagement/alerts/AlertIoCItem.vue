<template>
	<CardEntity :embedded hoverable>
		<template #default>
			<div class="flex flex-wrap gap-2">
				<strong>{{ ioc.type }}</strong>
				<span>{{ ioc.value }}</span>
			</div>
			<p class="mt-2">{{ ioc.description }}</p>
		</template>
		<template #footerExtra>
			<div class="flex items-center justify-end gap-3">
				<VirusTotalEnrichmentButton :ioc-value="ioc.value" />

				<n-popconfirm
					v-model:show="showDeleteConfirm"
					trigger="manual"
					to="body"
					@positive-click="deleteIoc()"
					@clickoutside="showDeleteConfirm = false"
				>
					<template #trigger>
						<n-button quaternary size="tiny" :loading="canceling" @click.stop="showDeleteConfirm = true">
							Delete
						</n-button>
					</template>
					Are you sure you want to delete this IoC?
				</n-popconfirm>
			</div>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { AlertIOC } from "@/types/incidentManagement/alerts"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import VirusTotalEnrichmentButton from "@/components/threatIntel/VirusTotalEnrichmentButton.vue"
import { NButton, NPopconfirm, useMessage } from "naive-ui"
import { ref } from "vue"

const { ioc, embedded, alertId } = defineProps<{
	ioc: AlertIOC
	alertId: number
	embedded?: boolean
}>()

const emit = defineEmits<{
	(e: "deleted"): void
}>()

const message = useMessage()
const canceling = ref(false)
const showDeleteConfirm = ref(false)

function deleteIoc() {
	canceling.value = true

	Api.incidentManagement
		.deleteAlertIoc(alertId, ioc.id)
		.then(res => {
			if (res.data.success) {
				message.success(res.data?.message || "Case Data Store File deleted successfully")
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
</script>
