<template>
	<div class="logo">
		<Transition name="logo-fade" mode="out-in">
			<img :key="logoSrc" :src="logoSrc" :alt="logoAlt" :aria-label="logoAlt" class="logo-image" />
		</Transition>
	</div>
</template>

<script lang="ts" setup>
import { computed } from "vue"
import { useThemeStore } from "@/stores/theme"

interface Props {
	type?: "default" | "mini" | "large"
	dark?: boolean
	maxHeight?: string
}

const props = withDefaults(defineProps<Props>(), {
	type: "default",
	maxHeight: "32px"
})

const themeStore = useThemeStore()

const isDark = computed<boolean>(() => props.dark ?? themeStore.isThemeDark)

const logoSrc = computed<string>(() => {
	const theme = isDark.value ? "dark" : "light"
	return new URL(`../../assets/images/socfortress_logo_${props.type}_${theme}.svg`, import.meta.url).href
})

const logoAlt = computed<string>(() => {
	const typeLabel = props.type === "mini" ? "Mini" : props.type === "large" ? "Large" : ""
	return `SOCFortress ${typeLabel} Logo`.trim()
})
</script>

<style lang="scss" scoped>
.logo {
	height: 100%;
	display: flex;
	align-items: center;
	justify-content: center;
	position: relative;

	.logo-image {
		max-height: v-bind(maxHeight);
		height: 100%;
		width: auto;
		display: block;
		object-fit: contain;
	}
}

// Smooth transition between theme changes
.logo-fade-enter-active,
.logo-fade-leave-active {
	transition: opacity 0.2s ease-in-out;
}

.logo-fade-enter-from,
.logo-fade-leave-to {
	opacity: 0;
}
</style>
