<template>
	<div class="license-viewer flex items-center justify-center gap-4" :class="{ 'has-side': !!key }">
		<div class="main-box">
			<LicenseFeatures
				:hide-key="!!key"
				:license-data="details"
				class="h-full"
				:class="{ 'mt-8': !key }"
				@license-key-loaded="licenseKeyLoaded"
			/>
		</div>
		<div class="side-box">
			<n-scrollbar style="max-width: 100%">
				<LicenseDetails v-if="key" hide-features class="min-h-full" @license-loaded="licenseLoaded" />
			</n-scrollbar>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { License, LicenseKey } from "@/types/license.d"
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

<style lang="scss" scoped>
.license-viewer {
	height: 100%;

	.main-box {
		width: 450px;
		min-width: 300px;
	}
	.side-box {
		overflow: hidden;
		transition: all 0.3s var(--bezier-ease);
		border-radius: var(--border-radius);
	}
	&.has-side {
		align-items: stretch;
		.side-box {
			flex-grow: 1;
		}
	}

	@media (max-width: 800px) {
		flex-direction: column;

		.main-box {
			width: unset;
			min-width: unset;
			max-width: unset;
		}
	}
}
</style>
