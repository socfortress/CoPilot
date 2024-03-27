<template>
	<n-spin :show="loading">
		<div class="license-box" :class="{ loading: !licenseKey }">
			<p class="flex gap-4 items-center">
				<span>your license:</span>
				<Icon :name="LoadingIcon" v-if="!licenseKey"></Icon>
			</p>
			<div class="flex items-center gap-4 mt-1" v-if="!replaceEnabled && licenseKey">
				<h3>{{ licenseKey }}</h3>
				<div class="actions-box flex gap-2">
					<n-button secondary :disabled="replaceEnabled" @click="enableReplace()" size="small">
						<template #icon>
							<Icon :name="EditIcon"></Icon>
						</template>
						Edit
					</n-button>
					<n-button
						type="primary"
						:loading="loadingExtend"
						@click="enableExtend()"
						v-if="!extendEnabled"
						size="small"
					>
						<template #icon>
							<Icon :name="ExtendIcon"></Icon>
						</template>
						Extend
					</n-button>
				</div>
			</div>
		</div>

		<div class="replace-box mt-2 flex gap-2" v-if="replaceEnabled">
			<n-input v-model:value="licenseKeyModel" class="grow !max-w-72" clearable />
			<n-button secondary :disabled="loadingReplace" @click="resetLicense()">Reset</n-button>
			<n-button type="success" :loading="loadingReplace" :disabled="!licenseKeyModel" @click="replaceLicense()">
				<template #icon>
					<Icon :name="EditIcon"></Icon>
				</template>
				Replace
			</n-button>
		</div>

		<div class="extend-box mt-5 flex gap-2" v-if="extendEnabled">
			<n-input-number v-model:value="period" class="grow !max-w-44" :min="1">
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
	</n-spin>
</template>

<script setup lang="ts">
import { NInput, NInputNumber, NButton, NSpin, useMessage } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import Api from "@/api"
import { onBeforeMount, ref } from "vue"
import { computed } from "vue"
import type { LicenseKey } from "@/types/license"

const emit = defineEmits<{
	(e: "updated"): void
}>()

const LoadingIcon = "eos-icons:loading"
const EditIcon = "uil:edit-alt"
const ExtendIcon = "majesticons:clock-plus-line"

const message = useMessage()
const loadingLicense = ref(false)
const loadingReplace = ref(false)
const loadingExtend = ref(false)

const licenseKey = ref<LicenseKey | "">("")
const licenseKeyModel = ref<LicenseKey | "">("")
const period = ref<number>(15)
const replaceEnabled = ref(false)
const extendEnabled = ref(false)

const loading = computed(() => loadingLicense.value || loadingReplace.value || loadingExtend.value)

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
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
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

onBeforeMount(() => {
	getLicense()
})
</script>

<style lang="scss" scoped>
.license-box.loading {
	min-height: 100px;
}
</style>
