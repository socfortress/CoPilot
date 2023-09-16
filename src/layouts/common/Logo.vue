<template>
	<div class="logo" v-if="isDark && !mini">
		<img src="@/assets/images/brand-logo_dark.svg?url" />
	</div>
	<div class="logo" v-else-if="isLight && !mini">
		<img src="@/assets/images/brand-logo_light.svg?url" />
	</div>
	<div class="logo" v-else-if="isDark && mini">
		<img src="@/assets/images/brand-icon_dark.svg?url" />
	</div>
	<div class="logo" v-else-if="isLight && mini">
		<img src="@/assets/images/brand-icon_light.svg?url" />
	</div>
</template>

<script lang="ts" setup>
import { useThemeStore } from "@/stores/theme"
import { computed, toRefs } from "vue"

defineOptions({
	name: "Logo"
})

const props = withDefaults(
	defineProps<{
		mini: boolean
		dark?: boolean
	}>(),
	{ dark: undefined }
)
const { mini, dark } = toRefs(props)

const isDark = computed<boolean>(() => dark.value ?? useThemeStore().isThemeDark)
const isLight = computed<boolean>(() => !dark.value ?? useThemeStore().isThemeLight)
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
