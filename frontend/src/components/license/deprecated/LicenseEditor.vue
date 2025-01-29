<template>
	<n-spin :show="loading">
		<div class="license-box" :class="{ loading: loadingLicense && !licenseKey }">
			<p v-if="loadingLicense || licenseKey" class="flex items-center gap-4">
				<span>your license:</span>
				<Icon v-if="loadingLicense" :name="LoadingIcon"></Icon>
			</p>
			<div v-if="!loadingLicense && !licenseKey">
				<p v-if="!creationEnabled" class="flex items-center gap-4">no license found</p>
				<div class="mt-2 flex items-center gap-4">
					<div class="actions-box flex gap-2">
						<n-button
							v-if="!creationEnabled"
							type="primary"
							:loading="loadingCreation"
							size="small"
							@click="enableCreation()"
						>
							<template #icon>
								<Icon :name="LicenseIcon"></Icon>
							</template>
							Create new license
						</n-button>
					</div>
				</div>
			</div>
			<div v-if="!replaceEnabled && licenseKey" class="mt-1 flex items-center gap-4">
				<h3>{{ licenseKey }}</h3>
				<div class="actions-box flex gap-2">
					<n-button secondary :disabled="replaceEnabled" size="small" @click="enableReplace()">
						<template #icon>
							<Icon :name="EditIcon"></Icon>
						</template>
						Edit
					</n-button>
					<n-button
						v-if="!extendEnabled"
						type="primary"
						:loading="loadingExtend"
						size="small"
						@click="enableExtend()"
					>
						<template #icon>
							<Icon :name="ExtendIcon"></Icon>
						</template>
						Extend
					</n-button>
				</div>
			</div>
		</div>

		<div v-if="replaceEnabled" class="replace-box mt-2 flex gap-2">
			<n-input v-model:value="licenseKeyModel" class="!max-w-72 grow" clearable />
			<n-button secondary :disabled="loadingReplace" @click="resetLicense()">Reset</n-button>
			<n-button type="success" :loading="loadingReplace" :disabled="!licenseKeyModel" @click="replaceLicense()">
				<template #icon>
					<Icon :name="EditIcon"></Icon>
				</template>
				Replace
			</n-button>
		</div>

		<div v-if="extendEnabled" class="extend-box mt-5 flex gap-2">
			<n-input-number v-model:value="period" class="!max-w-44 grow" :min="1">
				<template #prefix>
					<div class="min-w-12">Day{{ period === 1 ? "" : "s" }}</div>
				</template>
			</n-input-number>
			<n-button secondary :disabled="loadingExtend" @click="resetPeriod()">Reset</n-button>
			<n-button type="success" :loading="loadingExtend" :disabled="!period" @click="extendLicense()">
				<template #icon>
					<Icon :name="ExtendIcon"></Icon>
				</template>
				Extend
			</n-button>
		</div>

		<div v-if="creationEnabled" class="create-box flex flex-col gap-2">
			<n-form ref="formRef" :label-width="80" :model="creationForm" :rules="rules">
				<div class="grid-auto-fit-200 grid gap-2">
					<n-form-item label="Name" path="name">
						<n-input v-model:value.trim="creationForm.name" placeholder="Input name..." clearable />
					</n-form-item>
					<n-form-item label="Email" path="email">
						<n-input v-model:value.trim="creationForm.email" placeholder="Input email..." clearable />
					</n-form-item>
					<n-form-item label="Company Name" path="companyName">
						<n-input
							v-model:value.trim="creationForm.companyName"
							placeholder="Input Company Name..."
							clearable
						/>
					</n-form-item>
				</div>
			</n-form>
			<div class="flex justify-end gap-2">
				<n-button secondary :disabled="loadingCreation" @click="resetCreation()">Reset</n-button>
				<n-button
					type="success"
					:loading="loadingCreation"
					:disabled="!isCreationFormValid"
					@click="validateCreation()"
				>
					<template #icon>
						<Icon :name="LicenseIcon"></Icon>
					</template>
					Create License
				</n-button>
			</div>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
/** @deprecated */
import type { NewLicensePayload } from "@/api/endpoints/license"
import type { LicenseKey } from "@/types/license.d"
import type { FormInst, FormItemRule, FormRules, FormValidationError } from "naive-ui"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { NButton, NForm, NFormItem, NInput, NInputNumber, NSpin, useMessage } from "naive-ui"
import isEmail from "validator/es/lib/isEmail"
import { computed, onBeforeMount, ref } from "vue"

const emit = defineEmits<{
	(e: "updated"): void
}>()

const LoadingIcon = "eos-icons:loading"
const EditIcon = "uil:edit-alt"
const LicenseIcon = "carbon:license"
const ExtendIcon = "majesticons:clock-plus-line"

const formRef = ref<FormInst>()
const message = useMessage()
const loadingLicense = ref(false)
const loadingReplace = ref(false)
const loadingExtend = ref(false)
const loadingCreation = ref(false)

const licenseKey = ref<LicenseKey | "">("")
const licenseKeyModel = ref<LicenseKey | "">("")
const period = ref<number>(15)
const creationForm = ref<NewLicensePayload>(getCreationForm())
const replaceEnabled = ref(false)
const extendEnabled = ref(false)
const creationEnabled = ref(false)

const isCreationFormValid = computed(() => {
	if (!creationForm.value.name || !creationForm.value.email || !creationForm.value.companyName) {
		return false
	}
	return true
})

const loading = computed(
	() => loadingLicense.value || loadingReplace.value || loadingExtend.value || loadingCreation.value
)

const rules: FormRules = {
	name: {
		required: true,
		message: "Please input name",
		trigger: ["input", "blur"]
	},
	companyName: {
		required: true,
		message: "Please input company name",
		trigger: ["input", "blur"]
	},
	email: {
		required: true,
		trigger: ["input", "blur"],
		validator: (rule: FormItemRule, value: string) => {
			if (!value) {
				return new Error("Email is required")
			}
			if (!isEmail(value)) {
				return new Error("The email is not formatted correctly")
			}
		}
	}
}

function getLicense() {
	loadingLicense.value = true

	Api.license
		.getLicense()
		.then(res => {
			if (res.data.success) {
				licenseKey.value = res.data?.license_key || ""
				licenseKeyModel.value = res.data?.license_key || ""
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			if (err.response.status !== 404) {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			}
		})
		.finally(() => {
			loadingLicense.value = false
		})
}

function replaceLicense() {
	if (licenseKeyModel.value) {
		loadingReplace.value = true

		Api.license
			.replaceLicense(licenseKeyModel.value)
			.then(res => {
				if (res.data.success) {
					disableReplace()
					message.success(res.data?.message || "License replaced successfully")
					emit("updated")
					getLicense()
				} else {
					message.warning(res.data?.message || "An error occurred. Please try again later.")
				}
			})
			.catch(err => {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			})
			.finally(() => {
				loadingReplace.value = false
			})
	}
}

function extendLicense() {
	if (period.value) {
		loadingExtend.value = true

		Api.license
			.extendLicense(period.value)
			.then(res => {
				if (res.data.success) {
					resetPeriod()
					message.success(res.data?.message || "License extended successfully")
					emit("updated")
				} else {
					message.warning(res.data?.message || "An error occurred. Please try again later.")
				}
			})
			.catch(err => {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			})
			.finally(() => {
				loadingExtend.value = false
			})
	}
}

function createLicense() {
	loadingCreation.value = true

	Api.license
		.createLicense(creationForm.value)
		.then(res => {
			if (res.data.success) {
				resetCreation()
				message.success(res.data?.message || "License created successfully")
				emit("updated")
				getLicense()
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingCreation.value = false
		})
}

function resetLicense() {
	licenseKeyModel.value = licenseKey.value
	disableReplace()
}

function disableReplace() {
	replaceEnabled.value = false
}

function enableReplace() {
	resetPeriod()
	replaceEnabled.value = true
}

function resetPeriod() {
	period.value = 15
	disableExtend()
}

function disableExtend() {
	extendEnabled.value = false
}

function enableExtend() {
	extendEnabled.value = true
}

function resetCreation() {
	creationForm.value = getCreationForm()
	disableCreation()
}

function disableCreation() {
	creationEnabled.value = false
}

function enableCreation() {
	creationEnabled.value = true
}

function getCreationForm(): NewLicensePayload {
	return {
		name: "",
		email: "",
		companyName: ""
	}
}

function validateCreation() {
	if (!formRef.value) return

	formRef.value.validate((errors?: Array<FormValidationError>) => {
		if (!errors) {
			createLicense()
		} else {
			message.warning("You must fill in the required fields correctly.")
			return false
		}
	})
}

onBeforeMount(() => {
	getLicense()
})
</script>

<style lang="scss" scoped>
.license-box {
	&.loading {
		min-height: 100px;
	}
}
</style>
