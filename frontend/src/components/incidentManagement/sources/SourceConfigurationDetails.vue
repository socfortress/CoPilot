<template>
	<n-spin :show="loading || submitting" class="min-h-20">
		<SourceConfigurationViewer v-if="sourceConfiguration" v-show="!editing" :source-configuration />

		<div v-if="!editing && !loading" class="mt-4 flex items-center justify-end gap-2">
			<n-button @click="setEditMode()">
				<template #icon>
					<Icon :name="EditIcon" :size="16"></Icon>
				</template>
				Edit
			</n-button>
		</div>

		<SourceConfigurationForm
			v-if="sourceConfiguration"
			v-show="editing"
			:source-configuration-model="sourceConfiguration"
			show-index-name-field
			@mounted="formCTX = $event"
			@submitted="updateSourceConfiguration($event)"
		>
			<template #additionalActions>
				<n-button @click="setViewMode()">
					<template #icon>
						<Icon :name="ArrowIcon" :size="16"></Icon>
					</template>
					Cancel
				</n-button>
			</template>
		</SourceConfigurationForm>
	</n-spin>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common.d"
import type { SourceConfiguration, SourceName } from "@/types/incidentManagement/sources.d"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { NButton, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import SourceConfigurationForm from "./SourceConfigurationForm.vue"
import SourceConfigurationViewer from "./SourceConfigurationViewer.vue"

const { source } = defineProps<{ source: SourceName }>()

const message = useMessage()
const loading = ref(false)
const submitting = ref(false)
const ArrowIcon = "carbon:arrow-left"
const EditIcon = "uil:edit-alt"
const sourceConfiguration = ref<SourceConfiguration | null>(null)
const editing = ref(false)
const formCTX = ref<{ reset: () => void; toggleSubmittingFlag: () => boolean } | null>(null)

function getSourceConfiguration() {
	loading.value = true

	Api.incidentManagement
		.getSourceConfiguration(source)
		.then(res => {
			if (res.data.success) {
				sourceConfiguration.value = {
					field_names: res.data.field_names || [],
					asset_name: res.data.asset_name || "",
					timefield_name: res.data.timefield_name || "",
					alert_title_name: res.data.alert_title_name || "",
					source: res.data.source || source
				}
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

function setEditMode() {
	formCTX.value?.reset()
	editing.value = true
}
function setViewMode() {
	editing.value = false
}

function updateSourceConfiguration(payload: SourceConfiguration) {
	submitting.value = formCTX.value?.toggleSubmittingFlag() || true

	Api.incidentManagement
		.updateSourceConfiguration(payload)
		.then(res => {
			if (res.data.success) {
				message.success(res.data?.message || `Source Configuration sent successfully`)
				getSourceConfiguration()
				setViewMode()
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch((err: ApiError) => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			submitting.value = formCTX.value?.toggleSubmittingFlag() || false
		})
}

onBeforeMount(() => {
	getSourceConfiguration()
})
</script>
