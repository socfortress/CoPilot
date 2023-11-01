<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Vue MapLibre</div>
			<div class="links">
				<a
					href="https://github.com/razorness/vue-maplibre-gl"
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

<script lang="ts" setup>
import { NCard, NSpin } from "naive-ui"
import { useThemeStore } from "@/stores/theme"

import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
import { ref, onMounted, defineAsyncComponent, type Component } from "vue"

const Map = defineAsyncComponent<Component>(() => import("@/components/maps/maplibre/Map.vue"))
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
