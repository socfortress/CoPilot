<template>
	<div v-if="isDark && !mini" class="logo">
		<img alt="logo" src="@/assets/images/socfortress_logo.svg?url" />
	</div>
	<div v-else-if="isLight && !mini" class="logo">
		<img alt="logo" src="@/assets/images/socfortress_logo.svg?url" />
	</div>
	<div v-else-if="isDark && mini" class="logo">
		<img alt="logo" src="@/assets/images/socfortress_logo.svg?url" />
	</div>
	<div v-else-if="isLight && mini" class="logo">
		<img alt="logo" src="@/assets/images/socfortress_logo.svg?url" />
	</div>
</template>

<script lang="ts" setup>
import { useThemeStore } from "@/stores/theme"
import { computed } from "vue"

const { mini, dark } = defineProps<{
	mini: boolean
	dark?: boolean
}>()
const themeStore = useThemeStore()
const isDark = computed<boolean>(() => dark ?? themeStore.isThemeDark)
const isLight = computed<boolean>(() => !dark || themeStore.isThemeLight)
</script>

<style lang="scss" scoped>
.logo {
	height: 100%;
	display: flex;
	align-items: center;

	img {
		max-height: 32px;
		display: block;
		height: 100%;
	}

	&.fade-enter-active,
	&.fade-leave-active {
		transition: opacity var(--sidebar-anim-ease) var(--sidebar-anim-duration);
	}

	&.fade-enter-from,
	&.fade-leave-to {
		opacity: 0;
	}
}
</style>
