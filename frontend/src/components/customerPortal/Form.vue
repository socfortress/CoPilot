<template>
	<n-spin :show="loading" content-class="flex grow flex-col">
		<div class="flex flex-col gap-4">
			<n-alert type="info" :bordered="false">
				Customize the customer portal login page title and logo shown to end customers.
			</n-alert>

			<CardEntity embedded size="small">
				<template #headerMain>
					<span class="text-xs font-semibold uppercase opacity-60">Portal branding</span>
				</template>

				<template #default>
					<div class="flex flex-col gap-4">
						<n-form-item label="Title" path="title" :show-feedback="false">
							<n-input v-model:value="model.title" clearable placeholder="CoPilot" />
						</n-form-item>

						<div class="flex flex-col gap-2">
							<span class="text-secondary text-xs font-medium">Logo</span>
							<div class="flex flex-wrap items-center gap-4">
								<div
									v-if="model.logo"
									class="group border-border relative size-17 shrink-0 overflow-hidden rounded-lg border"
								>
									<img :src="model.logo" alt="Portal logo preview" class="size-full object-cover" />
									<button
										type="button"
										class="absolute inset-0 flex cursor-pointer items-center justify-center bg-black/40 opacity-0 transition-opacity group-hover:opacity-100"
										@click="model.logo = null"
									>
										<Icon :name="RemoveIcon" :size="20" class="text-white" />
									</button>
								</div>
								<div
									v-else
									class="border-border bg-secondary flex size-17 shrink-0 items-center justify-center rounded-lg border border-dashed"
								>
									<Icon :name="LogoIcon" :size="24" class="text-secondary opacity-50" />
								</div>

								<ImageCropper
									v-slot="{ openCropper }"
									placeholder="Select a Logo"
									@crop="setCroppedImage"
								>
									<n-button secondary @click="openCropper()">
										<template #icon>
											<Icon :name="EditIcon" />
										</template>
										{{ model.logo ? "Change logo" : "Upload logo" }}
									</n-button>
								</ImageCropper>
							</div>
						</div>
					</div>
				</template>
			</CardEntity>

			<div class="flex justify-end">
				<n-button type="primary" :loading @click="save()">
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
import type { CustomerPortalSettingsPayload } from "@/api/endpoints/customer-portal"
import type { ImageCropperResult } from "@/components/common/ImageCropper.vue"
import type { ApiError } from "@/types/common"
import type { CustomerPortalSettings } from "@/types/customer-portal"
import _split from "lodash/split"
import { NAlert, NButton, NFormItem, NInput, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import ImageCropper from "@/components/common/ImageCropper.vue"
import { getApiErrorMessage } from "@/utils"

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
const LogoIcon = "carbon:image"
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

const DATA_URL_MIME_REGEX = /data:([^;]+);base64/

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
	const mimeMatch = parts[0]?.match(DATA_URL_MIME_REGEX)
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
				emit("success")
			} else {
				message.warning(res.data?.message || "Failed to update metadata")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred while updating metadata")
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
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
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
