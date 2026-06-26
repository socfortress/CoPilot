<template>
	<div class="flex h-full justify-center gap-4 max-[800px]:flex-col" :class="key ? 'items-stretch' : 'items-center'">
		<div class="w-112.5 min-w-75 max-[800px]:w-auto max-[800px]:max-w-none max-[800px]:min-w-0">
			<LicenseFeatures
				:hide-key="!!key"
				:license-data="details"
				class="h-full"
				:class="{ 'mt-8': !key }"
				@license-key-loaded="licenseKeyLoaded"
			/>
		</div>
		<div class="overflow-hidden rounded-lg transition-all duration-300" :class="{ grow: key }">
			<n-scrollbar class="w-full">
				<LicenseDetails v-if="key" hide-features class="min-h-full" @license-loaded="licenseLoaded" />
			</n-scrollbar>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { License, LicenseKey } from "@/types/license"
import { NScrollbar } from "naive-ui"
import { ref } from "vue"
import LicenseDetails from "./LicenseDetails.vue"
import LicenseFeatures from "./LicenseFeatures.vue"

const emit = defineEmits<{
	(e: "licenseKeyLoaded", value: LicenseKey): void
}>()

const key = ref<LicenseKey | undefined>(undefined)
const details = ref<License | undefined>(undefined)

function licenseKeyLoaded(licenseKey: LicenseKey) {
	key.value = licenseKey
	emit("licenseKeyLoaded", licenseKey)
}

function licenseLoaded(license: License) {
	details.value = license
}
</script>
