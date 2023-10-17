<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Leaflet</div>
			<div class="links">
				<a
					href="https://github.com/vue-leaflet/vue-leaflet"
					target="_blank"
					alt="docs"
					rel="nofollow noopener noreferrer"
				>
					<Icon :name="ExternalIcon" :size="16" />
					docs
				</a>
			</div>
		</div>

		<n-card>
			<div style="height: 60vh; width: 100%">
				<Map v-if="mounted" />
				<n-spin v-else class="w-full h-full"></n-spin>
			</div>
		</n-card>
	</div>
</template>
<script setup lang="ts">
import { NCard, NSpin } from "naive-ui"
import { defineAsyncComponent, onMounted, type Component } from "vue"
import { useThemeStore } from "@/stores/theme"

import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
import { ref } from "vue"

const Map = defineAsyncComponent<Component>(() => import("@/components/maps/leaflet/Map.vue"))
const mounted = ref(false)
const themeStore = useThemeStore()

onMounted(() => {
	const duration = 1000 * themeStore.routerTransitionDuration
	const gap = 500

	// TIMEOUT REQUIRED BY PAGE ANIMATION
	setTimeout(() => {
		mounted.value = true
	}, duration + gap)
})
</script>

<style lang="scss" scoped>
.page {
	:deep() {
		.leaflet-map-pane,
		.leaflet-control-container,
		.leaflet-control-attribution,
		.leaflet-bottom,
		.leaflet-top {
			z-index: 1;
		}
	}
}
</style>
