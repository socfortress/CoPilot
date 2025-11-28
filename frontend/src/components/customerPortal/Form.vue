<template>
	<n-spin :show="loading" content-class="flex grow flex-col">
		<div class="flex flex-col gap-4">
			<div class="grid grid-cols-1 gap-x-6 gap-y-2 md:grid-cols-2">
				<n-form-item label="Title" path="title">
					<n-input :value="model.title" />
				</n-form-item>

				<!-- Integration Name (readonly) -->
				<n-form-item label="Logo" path="logo">
					<n-input :value="model.logo" />
				</n-form-item>
			</div>

			<!-- Edit Form Actions -->
			<div class="flex items-center justify-between gap-3">
				<n-button type="primary" :loading="loading" @click="save()">
					<template #icon>
						<Icon :name="SaveIcon"></Icon>
					</template>
					Save Changes
				</n-button>
			</div>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { CustomerPortalSettingsPayload } from "@/api/endpoints/customerPortal"
import type { CustomerPortalSettings } from "@/types/customerPortal"
import { NButton, NFormItem, NInput, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"

interface Model {
	title: string | null
	logo: File | null
}

const emit = defineEmits<{
	(e: "success"): void
}>()

const SaveIcon = "carbon:save"
const message = useMessage()
const loading = ref(false)
const settings = ref<CustomerPortalSettings | null>(null)
const model = ref<Model>(getDefaultModel())

function getDefaultModel(entity?: CustomerPortalSettings): Model {
	return {
		title: entity?.title || "",
		logo: null
	}
}

function save() {
	loading.value = true

	const payload: CustomerPortalSettingsPayload = {
		title: "",
		logo_base64: "",
		logo_mime_type: ""
	}

	Api.customerPortal
		.setSettings(payload)
		.then(res => {
			if (res.data.success) {
				message.success(res.data?.message || "Customer Portal settings updated successfully")
				// Reload the data to show updated values
				emit("success")
			} else {
				message.warning(res.data?.message || "Failed to update metadata")
			}
		})
		.catch(err => {
			const errorMsg = err.response?.data?.message || "An error occurred while updating metadata"
			message.error(errorMsg)
		})
		.finally(() => {
			loading.value = false
		})
}

function getSettings() {
	loading.value = true

	Api.customerPortal
		.getSettings()
		.then(res => {
			if (res.data.success) {
				settings.value = res.data.settings
				model.value = getDefaultModel(settings.value)
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
	getSettings()
})
</script>
