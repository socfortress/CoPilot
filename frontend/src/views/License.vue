<template>
	<div class="page flex flex-col gap-8">
		<LicenseEditor @updated="reload()" />
		<LicenseViewer @mounted="licenseViewerCTX = $event" hide-key />
	</div>
</template>

<script setup lang="ts">
import LicenseEditor from "@/components/license/LicenseEditor.vue"
import LicenseViewer from "@/components/license/LicenseViewer.vue"
import { ref } from "vue"

const licenseViewerCTX = ref<{ reload: () => void } | null>(null)

function reload() {
	if (licenseViewerCTX.value) {
		licenseViewerCTX.value.reload()
	}
}
</script>
