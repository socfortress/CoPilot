<template>
	<button class="fullscreen-switch" @click="toggleFullscreen" alt="fullscreen-switch" aria-label="fullscreen-switch">
		<Icon :size="20" :name="CloseIcon" v-if="isFullscreen"></Icon>
		<Icon :size="20" :name="OpenIcon" v-else></Icon>
	</button>
</template>

<script lang="ts" setup>
import Icon from "@/components/common/Icon.vue"
import { useFullscreenSwitch } from "@/composables/useFullscreenSwitch"

const { isFullscreen, toggle } = useFullscreenSwitch()

const OpenIcon = "fluent:full-screen-maximize-24-regular"
const CloseIcon = "fluent:full-screen-minimize-24-regular"

defineOptions({
	name: "FullscreenSwitch"
})

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
