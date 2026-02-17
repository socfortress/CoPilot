<template>
	<n-spin :show="loading" content-class="flex grow flex-col">
		<div class="flex flex-col gap-10">
			<n-form-item label="Title" path="title" :show-feedback="false">
				<n-input v-model:value="model.title" clearable />
			</n-form-item>

			<div class="flex gap-3">
				<div v-if="model.logo" class="relative">
					<div
						class="absolute inset-0 flex cursor-pointer items-center justify-center bg-black/10 opacity-0 transition-opacity duration-300 hover:opacity-100"
						@click="model.logo = null"
					>
						<Icon :name="RemoveIcon" :size="30" class="text-secondary drop-shadow-md/90" />
					</div>

					<img :src="model.logo" width="66" height="66" class="object-cover" />
				</div>
				<n-form-item label="Logo" path="logo" :show-feedback="false">
					<ImageCropper v-slot="{ openCropper }" placeholder="Select a Logo" @crop="setCroppedImage">
						<n-button @click="openCropper()">
							<template #icon>
								<Icon :name="EditIcon" />
							</template>
							Edit Logo Image
						</n-button>
					</ImageCropper>
				</n-form-item>
			</div>

			<div>
				<n-button type="primary" :loading="loading" @click="save()">
					<template #icon>
						<Icon :name="SaveIcon" />
					</template>
					Save Changes
				</n-button>
			</div>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
// TODO: refactor
import type { CustomerPortalSettingsPayload } from "@/api/endpoints/customerPortal"
import type { ImageCropperResult } from "@/components/common/ImageCropper.vue"
import type { CustomerPortalSettings } from "@/types/customerPortal"
import _split from "lodash/split"
import { NButton, NFormItem, NInput, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import ImageCropper from "@/components/common/ImageCropper.vue"

export interface SettingsModel {
	title: string | null
	logo: string | null
}

const emit = defineEmits<{
	(e: "update", value: SettingsModel): void
	(e: "success"): void
}>()

const SaveIcon = "carbon:save"
const EditIcon = "uil:image-edit"
const RemoveIcon = "carbon:trash-can"
const message = useMessage()
const loading = ref(false)
const settings = ref<CustomerPortalSettings | null>(null)
const model = ref<SettingsModel>(getDefaultModel())

function setCroppedImage(result: ImageCropperResult) {
	const canvas = result.canvas as HTMLCanvasElement
	model.value.logo = canvas.toDataURL()
}

function getDefaultModel(entity?: CustomerPortalSettings): SettingsModel {
	return {
		title: entity?.title || "",
		logo:
			entity?.logo_base64 && entity?.logo_mime_type
				? `data:${entity.logo_mime_type};base64,${entity.logo_base64}`
				: null
	}
}

function getLogoMeta(logo?: string | null): { base64: string | null; mime_type: string | null } {
	// Parse data URL format: data:image/png;base64,iVBORw0KG...
	const parts = _split(logo, ",")
	if (!logo || parts.length !== 2) {
		return {
			base64: null,
			mime_type: null
		}
	}

	const base64 = parts[1]
	const mimeMatch = parts[0]?.match(/data:([^;]+);base64/)
	const mime_type = mimeMatch ? mimeMatch[1] : null

	return {
		base64: base64 ?? null,
		mime_type: mime_type ?? null
	}
}

function save() {
	loading.value = true

	const payload: CustomerPortalSettingsPayload = {
		title: model.value.title || null,
		logo_base64: getLogoMeta(model.value.logo).base64,
		logo_mime_type: getLogoMeta(model.value.logo).mime_type
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

watch(
	model,
	val => {
		emit("update", val)
	},
	{ immediate: true, deep: true }
)

onBeforeMount(() => {
	getSettings()
})
</script>
