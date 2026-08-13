<template>
	<n-spin :show="loading || submitting" class="min-h-20">
		<SourceConfigurationViewer v-if="sourceConfiguration" v-show="!editing" :source-configuration />

		<div v-if="!editing && !loading" class="mt-4 flex items-center justify-end gap-4">
			<n-button @click="setEditMode()">
				<template #icon>
					<Icon :name="EditIcon" :size="16" />
				</template>
				Edit
			</n-button>

			<n-button v-if="deletable" text type="error" ghost :loading="deleting" @click="handleDelete()">
				<template #icon>
					<Icon :name="DeleteIcon" :size="15" />
				</template>
				Delete
			</n-button>
		</div>

		<SourceConfigurationForm
			v-if="sourceConfiguration"
			v-show="editing"
			ref="formRef"
			:source-configuration-model="sourceConfiguration"
			show-index-name-field
			@submitted="updateSourceConfiguration($event)"
		>
			<template #additionalActions>
				<n-button @click="setViewMode()">
					<template #icon>
						<Icon :name="ArrowIcon" :size="16" />
					</template>
					Cancel
				</n-button>
			</template>
		</SourceConfigurationForm>
	</n-spin>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { SourceConfiguration, SourceName } from "@/types/incidentManagement/sources"
import { NButton, NSpin, useDialog, useMessage } from "naive-ui"
import { h, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"
import SourceConfigurationForm from "./SourceConfigurationForm.vue"
import SourceConfigurationViewer from "./SourceConfigurationViewer.vue"

const { source, deletable = false } = defineProps<{
	source: SourceName
	deletable?: boolean
}>()

const emit = defineEmits<{
	(e: "deleted"): void
}>()

const message = useMessage()
const dialog = useDialog()
const loading = ref(false)
const submitting = ref(false)
const deleting = ref(false)
const ArrowIcon = "carbon:arrow-left"
const EditIcon = "uil:edit-alt"
const DeleteIcon = "ph:trash"
const sourceConfiguration = ref<SourceConfiguration | null>(null)
const editing = ref(false)
const formRef = ref<{ reset: () => void; toggleSubmittingFlag: () => boolean } | null>(null)

function getSourceConfiguration() {
	loading.value = true

	Api.incidentManagement.sources
		.getSourceConfiguration(source)
		.then(res => {
			if (res.data.success) {
				sourceConfiguration.value = {
					field_names: res.data.field_names || [],
					ioc_field_names: res.data.ioc_field_names || [],
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
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

function setEditMode() {
	formRef.value?.reset()
	editing.value = true
}
function setViewMode() {
	editing.value = false
}

function updateSourceConfiguration(payload: SourceConfiguration) {
	submitting.value = formRef.value?.toggleSubmittingFlag() || true

	Api.incidentManagement.sources
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
			message.error(getApiErrorMessage(err) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			submitting.value = formRef.value?.toggleSubmittingFlag() || false
		})
}

onBeforeMount(() => {
	getSourceConfiguration()
})

function deleteSourceConfiguration() {
	deleting.value = true

	Api.incidentManagement.sources
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
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			deleting.value = false
		})
}

function handleDelete() {
	dialog.warning({
		title: "Confirm",
		content: () =>
			h("div", {
				innerHTML: `Are you sure you want to delete the source configuration for <strong>${source}</strong>?`
			}),
		positiveText: "Yes I'm sure",
		negativeText: "Cancel",
		onPositiveClick: () => {
			deleteSourceConfiguration()
		},
		onNegativeClick: () => {
			message.info("Delete canceled")
		}
	})
}
</script>
