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
import { computed } from "vue"
import { useThemeStore } from "@/stores/theme"

const {
	mini,
	dark,
	maxHeight = "32px"
} = defineProps<{
	mini?: boolean
	dark?: boolean
	maxHeight?: string
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
		max-height: v-bind(maxHeight);
		display: block;
		height: 100%;
	}
}
</style>
