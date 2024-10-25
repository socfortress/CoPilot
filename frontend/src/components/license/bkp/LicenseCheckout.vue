<template>
	<div class="license-box flex items-center justify-between gap-1">
		<div class="flex flex-col gap-1">
			<p class="flex items-center gap-4">
				<span>license</span>
				<Icon v-if="loadingLicense" :name="LoadingIcon"></Icon>
			</p>

			<h3 v-if="!loadingLicense">
				{{ licenseKey || "No license found" }}
			</h3>
		</div>

		<div v-if="!loadingLicense" class="actions-box mr-2 flex gap-2">
			<n-button type="primary" @click="openCheckout()">
				<template #icon>
					<Icon :name="licenseKey ? ExtendIcon : LicenseIcon"></Icon>
				</template>
				{{ licenseKey ? "Extend license" : "Create new license" }}
			</n-button>
		</div>
	</div>

	<n-modal
		v-model:show="showCheckoutForm"
		preset="card"
		:style="{ maxWidth: 'min(600px, 90vw)', minHeight: 'min(300px, 90vh)', overflow: 'hidden' }"
		:title="licenseKey ? 'Update License' : 'Add License'"
		:bordered="false"
		content-class="flex flex-col"
		segmented
	>
		<LicenseCheckoutWizard />
	</n-modal>
</template>

<script setup lang="ts">
import type { LicenseKey } from "@/types/license.d"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { NButton, NModal, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import LicenseCheckoutWizard from "./LicenseCheckoutWizard.vue"

const emit = defineEmits<{
	(e: "loaded"): void
}>()

const LoadingIcon = "eos-icons:loading"
const LicenseIcon = "carbon:license"
const ExtendIcon = "carbon:intent-request-create"

const message = useMessage()
const showCheckoutForm = ref(false)
const loadingLicense = ref(false)

const licenseKey = ref<LicenseKey | "">("")

function openCheckout() {
	showCheckoutForm.value = true
}

function getLicense() {
	loadingLicense.value = true

	Api.license
		.getLicense()
		.then(res => {
			if (res.data.success) {
				// licenseKey.value = res.data?.license_key || ""
				if (licenseKey.value) {
					emit("loaded")
				}
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

onBeforeMount(() => {
	getLicense()
})
</script>

<style lang="scss" scoped>
.license-box {
	background-color: var(--bg-color);
	border-radius: var(--border-radius);
	padding: 14px 18px;
	.section {
		display: flex;
		flex-direction: column;
		gap: 6px;
		.label {
			display: flex;
			align-items: center;
			gap: 10px;
			color: var(--fg-secondary-color);
			font-family: var(--font-family-mono);
			font-size: 14px;
		}

		.value {
			font-size: 16px;
			font-weight: bold;
		}
	}
}
</style>
