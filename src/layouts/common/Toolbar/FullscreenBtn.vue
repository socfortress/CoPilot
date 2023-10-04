<template>
	<button class="fullscreen-switch" @click="toggleFullscreen" alt="fullscreen-switch" aria-label="fullscreen-switch">
		<n-icon size="20">
			<FullScreenMinimize24Regular v-if="isFullscreen" />
			<FullScreenMaximize24Regular v-else />
		</n-icon>
	</button>
</template>

<script lang="ts" setup>
import { NIcon } from "naive-ui"
import FullScreenMaximize24Regular from "@vicons/fluent/FullScreenMaximize24Regular"
import FullScreenMinimize24Regular from "@vicons/fluent/FullScreenMinimize24Regular"
import { useFullscreen } from "@vueuse/core"
import { emitter } from "@/emitter"
import { onMounted } from "vue"
const { isFullscreen, toggle } = useFullscreen()

defineOptions({
	name: "FullscreenBtn"
})

function toggleFullscreen(e?: MouseEvent) {
	toggle()
	return e
}

onMounted(() => {
	emitter.on("toggle:fullscreen", () => {
		toggleFullscreen()
	})
})
</script>

<style scoped lang="scss">
.fullscreen-switch {
	position: relative;
	width: 20px;
	height: 20px;
	overflow: hidden;
	outline: none;
	border: none;

	@media (max-width: 1000px) {
		display: none;
	}
}
</style>
