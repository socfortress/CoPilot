<template>
	<div class="page grow flex flex-col" :class="{ 'limit-height': licenseKey }">
		<LicenseViewer
			class="grow"
			:class="{ 'overflow-hidden': licenseKey }"
			@license-key-loaded="licenseKey = $event"
		/>
	</div>
</template>

<script setup lang="ts">
import LicenseViewer from "@/components/license/LicenseViewer.vue"
import type { LicenseKey } from "@/types/license"
import { ref } from "vue"

const licenseKey = ref<LicenseKey | undefined>(undefined)
</script>

<style lang="scss" scoped>
.page {
	&.limit-height {
		@media (min-width: 801px) {
			max-height: calc(100svh - var(--toolbar-height) - var(--view-padding) - var(--header-bar-height) - 66px);
			overflow: hidden;
		}
	}
}
</style>
