<template>
	<button
		class="hidden cursor-pointer items-center justify-center lg:flex"
		alt="fullscreen-switch"
		aria-label="fullscreen-switch"
		@click="toggle()"
	>
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
</script>
