<template>
	<button class="theme-switch" @click="toggleTheme" alt="theme-switch" aria-label="theme-switch">
		<Transition name="rotate">
			<n-icon size="20" v-if="isThemeDark">
				<Sunny class="hover" />
				<SunnyOutline />
			</n-icon>
			<n-icon size="20" v-else>
				<Moon class="hover" />
				<MoonOutline />
			</n-icon>
		</Transition>
	</button>
</template>

<script lang="ts" setup>
import { useThemeStore } from "@/stores/theme"
import { computed, onMounted } from "vue"
import { NIcon } from "naive-ui"
import Sunny from "@vicons/ionicons5/Sunny"
import Moon from "@vicons/ionicons5/Moon"
import SunnyOutline from "@vicons/ionicons5/SunnyOutline"
import MoonOutline from "@vicons/ionicons5/MoonOutline"
import { emitter } from "@/emitter"

defineOptions({
	name: "ThemeSwitch"
})

const isThemeDark = computed<boolean>(() => useThemeStore().isThemeDark)
function toggleTheme(e?: MouseEvent) {
	useThemeStore().toggleTheme()
	return e
}

onMounted(() => {
	emitter.on("toggle:darkmode", () => {
		toggleTheme()
	})
})
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
