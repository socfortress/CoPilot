<template>
	<n-spin :show="loading">
		<div class="flex flex-col-reverse gap-6 lg:flex-row">
			<div class="border-primary shrink-0 overflow-hidden rounded-lg border-2 bg-white p-4 pt-12 lg:w-100 lg:p-6">
				<Preview class="mx-auto" :title="previewTitle" :logo="previewLogo" />
			</div>

			<div class="flex grow flex-col gap-4">
				<n-alert type="info" :bordered="false">
					This customer's portal branding.
					<b>Inherit</b>
					uses the global Customer Portal settings;
					<b>Custom</b>
					overrides them for users of this customer only.
				</n-alert>

				<CardEntity embedded size="small">
					<template #headerMain>
						<span class="text-xs font-semibold uppercase opacity-60">Branding mode</span>
					</template>
					<template #headerExtra>
						<n-tag v-if="effective" :bordered="false" size="small" :type="brandingTagType">
							Currently: {{ effective.source === "custom" ? "Custom" : "Global defaults" }}
						</n-tag>
					</template>

					<template #default>
						<div class="flex flex-col gap-4">
							<n-radio-group v-model:value="mode">
								<n-radio-button value="inherit">Inherit global settings</n-radio-button>
								<n-radio-button value="custom">Custom branding</n-radio-button>
							</n-radio-group>

							<span class="text-secondary text-xs">
								{{
									mode === "inherit"
										? "This customer sees the global portal title, logo and brand color."
										: "Fields left empty below keep inheriting the global value."
								}}
							</span>
						</div>
					</template>
				</CardEntity>

				<CardEntity v-if="mode === 'custom'" embedded size="small">
					<template #headerMain>
						<span class="text-xs font-semibold uppercase opacity-60">Custom branding</span>
					</template>

					<template #default>
						<div class="flex flex-col gap-6">
							<n-form-item label="Title" path="title" :show-feedback="false">
								<div class="flex w-full flex-col gap-1">
									<n-input
										v-model:value="model.title"
										:disabled="loading"
										clearable
										:placeholder="globalTitle || 'CoPilot'"
									/>
									<span class="text-secondary text-xs">
										Leave empty to inherit
										<span class="font-medium">{{ globalTitle || "CoPilot" }}</span>
									</span>
								</div>
							</n-form-item>

							<n-form-item label="Logo" path="logo" :show-feedback="false">
								<div class="flex w-full flex-col gap-2">
									<div class="flex flex-wrap items-center gap-4">
										<div
											v-if="model.logo"
											class="group border-border relative size-17 shrink-0 overflow-hidden rounded-lg border"
										>
											<img
												:src="model.logo"
												alt="Customer portal logo preview"
												class="size-full object-cover"
											/>
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
									<span class="text-secondary text-xs">
										Leave empty to inherit the global portal logo.
									</span>
								</div>
							</n-form-item>

							<n-form-item label="Brand color" path="brand_color" :show-feedback="false">
								<n-color-picker
									v-model:value="model.brand_color"
									:show-alpha="false"
									:modes="['hex']"
									:swatches="brandSwatches"
								/>
								<n-button
									v-if="model.brand_color"
									quaternary
									size="tiny"
									@click="model.brand_color = null"
								>
									Reset
								</n-button>
							</n-form-item>

							<span class="text-secondary -mt-3 text-xs">
								Used to theme this customer's branded PDF reports. Leave empty to inherit the global
								brand color.
							</span>
						</div>
					</template>
				</CardEntity>

				<div class="flex flex-wrap justify-end gap-3">
					<n-button v-if="override" :loading="deleting" :disabled="loading" @click="removeOverride()">
						<template #icon>
							<Icon :name="RemoveIcon" />
						</template>
						Remove override
					</n-button>
					<n-button type="primary" :loading="saving" :disabled="loading" @click="save()">
						<template #icon>
							<Icon :name="SaveIcon" />
						</template>
						Save Changes
					</n-button>
				</div>
			</div>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { CustomerPortalBrandingPayload } from "@/api/endpoints/customer-portal"
import type { ImageCropperResult } from "@/components/common/ImageCropper.vue"
import type { ApiError } from "@/types/common"
import type { CustomerPortalBrandingOverride, CustomerPortalEffectiveBranding } from "@/types/customer-portal"
import _split from "lodash/split"
import {
	NAlert,
	NButton,
	NColorPicker,
	NFormItem,
	NInput,
	NRadioButton,
	NRadioGroup,
	NSpin,
	NTag,
	useMessage
} from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import ImageCropper from "@/components/common/ImageCropper.vue"
import Preview from "@/components/customerPortal/Preview.vue"
import { getApiErrorMessage } from "@/utils"

const { customerCode } = defineProps<{
	customerCode: string
}>()

const SaveIcon = "carbon:save"
const EditIcon = "uil:image-edit"
const RemoveIcon = "carbon:trash-can"
const LogoIcon = "carbon:image"
const brandSwatches = ["#fc862e", "#12c46a", "#215ac8", "#ee4b3b", "#8c6fe0", "#22c1dc", "#0f172a"]

const message = useMessage()
const loading = ref(false)
const saving = ref(false)
const deleting = ref(false)

const override = ref<CustomerPortalBrandingOverride | null>(null)
const effective = ref<CustomerPortalEffectiveBranding | null>(null)
/** The global defaults, kept separately so the "inherits X" hints stay accurate while editing. */
const globalTitle = ref<string>("")
const globalLogo = ref<string | null>(null)

const mode = ref<"inherit" | "custom">("inherit")
const model = ref<{ title: string | null; logo: string | null; brand_color: string | null }>({
	title: "",
	logo: null,
	brand_color: null
})

const brandingTagType = computed(() => (effective.value?.source === "custom" ? "success" : "default"))

// The preview mirrors what the portal will render: the edited override where set,
// otherwise the global default for that field.
const previewTitle = computed(() => {
	if (mode.value === "inherit") return globalTitle.value
	return model.value.title || globalTitle.value
})
const previewLogo = computed(() => {
	if (mode.value === "inherit") return globalLogo.value
	return model.value.logo || globalLogo.value
})

function toDataUrl(base64?: string | null, mimeType?: string | null): string | null {
	if (!base64) return null
	if (base64.startsWith("data:")) return base64
	return `data:${mimeType || "image/png"};base64,${base64}`
}

const DATA_URL_MIME_REGEX = /data:([^;]+);base64/

function getLogoMeta(logo?: string | null): { base64: string | null; mime_type: string | null } {
	// Parse data URL format: data:image/png;base64,iVBORw0KG...
	const parts = _split(logo, ",")
	if (!logo || parts.length !== 2) {
		return { base64: null, mime_type: null }
	}

	const mimeMatch = parts[0]?.match(DATA_URL_MIME_REGEX)

	return {
		base64: parts[1] ?? null,
		mime_type: mimeMatch ? (mimeMatch[1] ?? null) : null
	}
}

function setCroppedImage(result: ImageCropperResult) {
	const canvas = result.canvas as HTMLCanvasElement
	model.value.logo = canvas.toDataURL()
}

function applyOverride(entity: CustomerPortalBrandingOverride | null) {
	override.value = entity
	mode.value = entity?.enabled ? "custom" : "inherit"
	model.value = {
		title: entity?.title || "",
		logo: toDataUrl(entity?.logo_base64, entity?.logo_mime_type),
		brand_color: entity?.brand_color ?? null
	}
}

async function loadBranding() {
	loading.value = true

	try {
		// The global settings are the fallback shown in the hints/preview, so they are
		// fetched alongside the override rather than derived from the effective values
		// (which already have the override merged in).
		const [brandingRes, globalRes] = await Promise.all([
			Api.customerPortal.getCustomerBranding(customerCode),
			Api.customerPortal.getSettings()
		])

		if (brandingRes.data.success) {
			effective.value = brandingRes.data.effective
			applyOverride(brandingRes.data.override)
		} else {
			message.warning(brandingRes.data.message || "Failed to load customer branding")
		}

		if (globalRes.data.success && globalRes.data.settings) {
			globalTitle.value = globalRes.data.settings.title || "CoPilot"
			globalLogo.value = toDataUrl(globalRes.data.settings.logo_base64, globalRes.data.settings.logo_mime_type)
		}
	} catch (error) {
		message.error(getApiErrorMessage(error as ApiError) || "Failed to load customer branding")
	} finally {
		loading.value = false
	}
}

async function save() {
	const logoMeta = getLogoMeta(model.value.logo)
	const payload: CustomerPortalBrandingPayload = {
		enabled: mode.value === "custom",
		title: model.value.title || null,
		logo_base64: logoMeta.base64,
		logo_mime_type: logoMeta.mime_type,
		brand_color: model.value.brand_color || null
	}

	saving.value = true
	try {
		const res = await Api.customerPortal.setCustomerBranding(customerCode, payload)
		if (res.data.success) {
			effective.value = res.data.effective
			applyOverride(res.data.override)
			message.success(res.data.message || "Customer branding updated successfully")
		} else {
			message.warning(res.data.message || "Failed to update customer branding")
		}
	} catch (error) {
		message.error(getApiErrorMessage(error as ApiError) || "Failed to update customer branding")
	} finally {
		saving.value = false
	}
}

async function removeOverride() {
	deleting.value = true
	try {
		const res = await Api.customerPortal.deleteCustomerBranding(customerCode)
		if (res.data.success) {
			effective.value = res.data.effective
			applyOverride(null)
			message.success(res.data.message || "Customer branding override removed")
		} else {
			message.warning(res.data.message || "Failed to remove customer branding override")
		}
	} catch (error) {
		message.error(getApiErrorMessage(error as ApiError) || "Failed to remove customer branding override")
	} finally {
		deleting.value = false
	}
}

onBeforeMount(() => {
	loadBranding()
})
</script>
