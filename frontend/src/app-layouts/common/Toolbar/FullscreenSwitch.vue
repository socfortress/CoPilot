<template>
	<button class="fullscreen-switch" alt="fullscreen-switch" aria-label="fullscreen-switch" @click="toggleFullscreen">
		<Icon v-if="isFullscreen" :size="20" :name="CloseIcon" />
		<Icon v-else :size="20" :name="OpenIcon" />
	</button>
</template>

<script lang="ts" setup>
import Icon from "@/components/common/Icon.vue"
import { useFullscreenSwitch } from "@/composables/useFullscreenSwitch"

const { isFullscreen, toggle } = useFullscreenSwitch()
const OpenIcon = "fluent:full-screen-maximize-24-regular"
const CloseIcon = "fluent:full-screen-minimize-24-regular"

function toggleFullscreen(e?: MouseEvent) {
	toggle()
	return e
}
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
