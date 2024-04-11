<template>
	<div class="page grow flex flex-col" :class="{ 'page-wrapped': licenseKey }">
		<LicenseViewer class="grow" @license-key-loaded="licenseKey = $event" />
	</div>
</template>

<script setup lang="ts">
import LicenseViewer from "@/components/license/LicenseViewer.vue"
import type { LicenseKey } from "@/types/license"
import { ref } from "vue"

const licenseKey = ref<LicenseKey | undefined>(undefined)
</script>
