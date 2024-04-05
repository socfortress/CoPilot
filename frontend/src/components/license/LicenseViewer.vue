<template>
	<div class="license-viewer flex justify-center items-center gap-4" :class="{ 'has-side': !!license }">
		<div class="main-box">
			<LicenseFeatures @license-loaded="license = $event" :hide-key="!!license" class="h-full" />
		</div>
		<div class="side-box">
			<LicenseDetails hide-features :license="license" v-if="license" />
		</div>
	</div>
</template>

<script setup lang="ts">
import LicenseFeatures from "./LicenseFeatures.vue"
import LicenseDetails from "./LicenseDetails.vue"
import type { License } from "@/types/license"
import { ref } from "vue"

const license = ref<License | undefined>(undefined)
</script>

<style lang="scss" scoped>
.license-viewer {
	height: 100%;

	.main-box {
		max-width: 400px;
	}
	.side-box {
		overflow: hidden;
		transition: all 0.3s var(--bezier-ease);
	}
	&.has-side {
		align-items: stretch;
		.side-box {
			flex-grow: 1;
		}
	}
}
</style>
