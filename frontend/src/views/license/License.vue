<template>
	<div class="page flex grow flex-col" :class="{ 'limit-height': licenseKey }">
		<LicenseViewer
			class="grow"
			:class="{ 'overflow-hidden': licenseKey }"
			@license-key-loaded="licenseKey = $event"
		/>
	</div>
</template>

<script setup lang="ts">
import type { LicenseKey } from "@/types/license.d"
import { ref } from "vue"
import LicenseViewer from "@/components/license/LicenseViewer.vue"

const licenseKey = ref<LicenseKey | undefined>(undefined)
</script>

<style lang="scss" scoped>
.page {
	&.limit-height {
		@media (min-width: 801px) {
			max-height: calc(100dvh - var(--toolbar-height) - var(--view-padding) - var(--header-bar-height) - 66px);
			overflow: hidden;
		}
	}
}
</style>
