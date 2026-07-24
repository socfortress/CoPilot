<template>
	<n-spin :show="loading" content-class="flex grow flex-col">
		<div class="flex flex-col gap-4">
			<n-alert type="info" :bordered="false">
				<template v-if="isCustomerScope">
					This customer's portal branding.
					<b>Inherit</b>
					uses the global Customer Portal settings;
					<b>Custom</b>
					overrides them for users of this customer only.
				</template>
				<template v-else>
					Customize the customer portal login page title and logo shown to end customers. These are the
					<b>defaults</b>
					for every customer — a single customer can override them from its
					<b>Portal Branding</b>
					tab.
				</template>
			</n-alert>

			<CardEntity v-if="isCustomerScope" embedded size="small">
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
						<n-radio-group v-model:value="mode" :disabled="loading">
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

			<CardEntity v-if="showFields" embedded size="small">
				<template #headerMain>
					<span class="text-xs font-semibold uppercase opacity-60">
						{{ isCustomerScope ? "Custom branding" : "Portal branding" }}
					</span>
				</template>

				<template #default>
					<div class="flex flex-col gap-6">
						<n-form-item label="Title" path="title" :show-feedback="false">
							<div class="flex w-full flex-col gap-1">
								<n-input
									v-model:value="model.title"
									:disabled="loading"
									clearable
									:placeholder="fallbackTitle"
								/>
								<span v-if="isCustomerScope" class="text-secondary text-xs">
									Leave empty to inherit
									<span class="font-medium">{{ fallbackTitle }}</span>
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

									<ImageCropper v-slot="{ openCropper }" placeholder="Select a Logo" @crop="setCroppedImage">
										<n-button secondary @click="openCropper()">
											<template #icon>
												<Icon :name="EditIcon" />
											</template>
											{{ model.logo ? "Change logo" : "Upload logo" }}
										</n-button>
									</ImageCropper>
								</div>
								<span v-if="isCustomerScope" class="text-secondary text-xs">
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
							<n-button v-if="model.brand_color" quaternary size="tiny" @click="model.brand_color = null">
								Reset
							</n-button>
						</n-form-item>

						<span class="text-secondary -mt-3 text-xs">
							{{
								isCustomerScope
									? "Used to theme this customer's branded PDF reports. Leave empty to inherit the global brand color."
									: "Used to theme customer-branded PDF reports. Leave empty to derive it from the logo."
							}}
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
	</n-spin>
</template>

<script setup lang="ts">
import type { CustomerPortalBrandingPayload, CustomerPortalSettingsPayload } from "@/api/endpoints/customer-portal"
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
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import ImageCropper from "@/components/common/ImageCropper.vue"
import { getApiErrorMessage } from "@/utils"

/**
 * The branding form, in both of its scopes:
 *
 * - **global** (no `customerCode`) — edits `customer_portal_settings`, the defaults
 *   every customer inherits.
 * - **per-customer** (`customerCode` given) — edits that customer's override, with
 *   an Inherit/Custom switch and per-field "leave empty to inherit <global>" hints.
 *
 * The two scopes render the same fields and differ only in what they load/save and
 * in the inherit affordances, so they stay one component rather than two copies.
 */
export interface SettingsModel {
	title: string | null
	logo: string | null
	brand_color: string | null
}

const { customerCode } = defineProps<{
	/** Omit for the global defaults; pass a code to edit that customer's override. */
	customerCode?: string
}>()

const emit = defineEmits<{
	/** The values to preview — already resolved against the global defaults when inheriting. */
	(e: "update", value: SettingsModel): void
	(e: "success"): void
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

const isCustomerScope = computed(() => !!customerCode)

const model = ref<SettingsModel>(getDefaultModel())
/** Per-customer scope only: inherit the global defaults or override them. */
const mode = ref<"inherit" | "custom">("inherit")
const override = ref<CustomerPortalBrandingOverride | null>(null)
const effective = ref<CustomerPortalEffectiveBranding | null>(null)
/** The global defaults, kept aside so the "inherits X" hints and preview stay accurate while editing. */
const globalDefaults = ref<SettingsModel>(getDefaultModel())

const showFields = computed(() => !isCustomerScope.value || mode.value === "custom")
const brandingTagType = computed(() => (effective.value?.source === "custom" ? "success" : "default"))
const fallbackTitle = computed(() => globalDefaults.value.title || "CoPilot")

// What the portal will actually render: the edited values where set, otherwise the
// global default for that field. In global scope there is nothing to inherit from.
const preview = computed<SettingsModel>(() => {
	if (!isCustomerScope.value) return { ...model.value }
	if (mode.value === "inherit") return { ...globalDefaults.value }

	return {
		title: model.value.title || globalDefaults.value.title,
		logo: model.value.logo || globalDefaults.value.logo,
		brand_color: model.value.brand_color || globalDefaults.value.brand_color
	}
})

function getDefaultModel(entity?: {
	title?: string | null
	logo_base64?: string | null
	logo_mime_type?: string | null
	brand_color?: string | null
}): SettingsModel {
	return {
		title: entity?.title || "",
		logo: toDataUrl(entity?.logo_base64, entity?.logo_mime_type),
		brand_color: entity?.brand_color ?? null
	}
}

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

function setCroppedImage(result: ImageCropperResult) {
	const canvas = result.canvas as HTMLCanvasElement
	model.value.logo = canvas.toDataURL()
}

function applyOverride(entity: CustomerPortalBrandingOverride | null) {
	override.value = entity
	mode.value = entity?.enabled ? "custom" : "inherit"
	model.value = getDefaultModel(entity ?? undefined)
}

async function getSettings() {
	loading.value = true

	try {
		// The global settings are both the edit target (global scope) and the fallback
		// shown in the hints/preview (per-customer scope), so they are always fetched.
		const [globalRes, brandingRes] = await Promise.all([
			Api.customerPortal.getSettings(),
			customerCode ? Api.customerPortal.getCustomerBranding(customerCode) : undefined
		])

		if (globalRes.data.success) {
			globalDefaults.value = getDefaultModel(globalRes.data.settings)
			if (!isCustomerScope.value) {
				model.value = getDefaultModel(globalRes.data.settings)
			}
		} else {
			message.warning(globalRes.data?.message || "An error occurred. Please try again later.")
		}

		if (brandingRes) {
			if (brandingRes.data.success) {
				effective.value = brandingRes.data.effective
				applyOverride(brandingRes.data.override)
			} else {
				message.warning(brandingRes.data?.message || "Failed to load customer branding")
			}
		}
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
	} finally {
		loading.value = false
	}
}

async function save() {
	const logoMeta = getLogoMeta(model.value.logo)
	const payload: CustomerPortalSettingsPayload = {
		title: model.value.title || null,
		logo_base64: logoMeta.base64,
		logo_mime_type: logoMeta.mime_type,
		brand_color: model.value.brand_color || null
	}

	saving.value = true

	try {
		if (customerCode) {
			const brandingPayload: CustomerPortalBrandingPayload = { ...payload, enabled: mode.value === "custom" }
			const res = await Api.customerPortal.setCustomerBranding(customerCode, brandingPayload)

			if (res.data.success) {
				effective.value = res.data.effective
				applyOverride(res.data.override)
				message.success(res.data?.message || "Customer branding updated successfully")
				emit("success")
			} else {
				message.warning(res.data?.message || "Failed to update customer branding")
			}
		} else {
			const res = await Api.customerPortal.setSettings(payload)

			if (res.data.success) {
				globalDefaults.value = { ...model.value }
				message.success(res.data?.message || "Customer Portal settings updated successfully")
				emit("success")
			} else {
				message.warning(res.data?.message || "Failed to update settings")
			}
		}
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "An error occurred while updating settings")
	} finally {
		saving.value = false
	}
}

/** Per-customer scope only: drop the override row so the customer inherits the defaults. */
async function removeOverride() {
	if (!customerCode) return

	deleting.value = true

	try {
		const res = await Api.customerPortal.deleteCustomerBranding(customerCode)

		if (res.data.success) {
			effective.value = res.data.effective
			applyOverride(null)
			message.success(res.data?.message || "Customer branding override removed")
			emit("success")
		} else {
			message.warning(res.data?.message || "Failed to remove customer branding override")
		}
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Failed to remove customer branding override")
	} finally {
		deleting.value = false
	}
}

watch(
	preview,
	val => {
		emit("update", val)
	},
	{ immediate: true, deep: true }
)

onBeforeMount(() => {
	getSettings()
})
</script>
