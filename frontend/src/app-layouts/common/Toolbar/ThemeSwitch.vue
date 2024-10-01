<template>
	<button class="theme-switch" alt="theme-switch" aria-label="theme-switch" @click="toggleTheme">
		<Transition name="rotate">
			<Icon v-if="isThemeDark" :size="20">
				<Iconify :icon="Sunny" class="hover" />
				<Iconify :icon="SunnyOutline" />
			</Icon>
			<Icon v-else :size="20">
				<Iconify :icon="Moon" class="hover" />
				<Iconify :icon="MoonOutline" />
			</Icon>
		</Transition>
	</button>
</template>

<script lang="ts" setup>
import Icon from "@/components/common/Icon.vue"
import { useThemeStore } from "@/stores/theme"
import { Icon as Iconify } from "@iconify/vue"
import { computed, nextTick } from "vue"

const Sunny = "ion:sunny"
const Moon = "ion:moon"
const SunnyOutline = "ion:sunny-outline"
const MoonOutline = "ion:moon-outline"
const themeStore = useThemeStore()
const isThemeDark = computed<boolean>(() => themeStore.isThemeDark)

function toggleTheme(event?: MouseEvent) {
	const isAppearanceTransition =
		typeof document !== "undefined" &&
		document.startViewTransition &&
		!window.matchMedia("(prefers-reduced-motion: reduce)").matches

	if (!isAppearanceTransition || !event) {
		themeStore.toggleTheme()
		return
	}

	if (document?.startViewTransition) {
		const x = event.clientX ?? innerWidth / 2
		const y = event.clientY ?? innerHeight / 2
		const endRadius = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y))

		const transition = document.startViewTransition(async () => {
			themeStore.toggleTheme()
			await nextTick()
		})

		transition.ready.then(() => {
			const clipPath = [`circle(0px at ${x}px ${y}px)`, `circle(${endRadius}px at ${x}px ${y}px)`]
			// const clipPath = [`inset(50%)`, `inset(0)`]

			document.documentElement.animate(
				{
					clipPath
				},
				{
					duration: 300,
					easing: "ease-in",
					pseudoElement: "::view-transition-new(root)"
				}
			)
		})
	}
}
</script>

<style scoped lang="scss">
.theme-switch {
	position: relative;
	width: 20px;
	height: 20px;
	overflow: hidden;
	outline: none;
	border: none;

	:deep() {
		.n-icon {
			position: absolute;
			top: 0;
			left: 0;

			& > svg {
				position: absolute;
				top: 0;
				left: 0;
				transition: opacity 0.35s;

				&.hover {
					opacity: 0;
				}
				&:not(.hover) {
					opacity: 1;
				}
			}

			&:hover {
				& > svg {
					&.hover {
						opacity: 1;
					}
					&:not(.hover) {
						opacity: 0;
					}
				}
			}
		}
	}
}
.rotate-enter-active,
.rotate-leave-active {
	transition: all 0.5s ease-out;
}
.rotate-enter-from {
	opacity: 0;
	transform: rotate(45deg);
}
.rotate-leave-to {
	opacity: 0;
	transform: rotate(-45deg);
}
</style>
