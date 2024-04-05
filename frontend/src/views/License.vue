<template>
	<div class="page grow flex flex-col" :class="{ 'page-wrapped': license }">
		<LicenseViewer class="grow" @license-loaded="license = $event" />
	</div>
</template>

<script setup lang="ts">
import LicenseViewer from "@/components/license/LicenseViewer.vue"
import type { LicenseKey } from "@/types/license"
import { ref } from "vue"

const license = ref<LicenseKey | undefined>(undefined)
</script>
