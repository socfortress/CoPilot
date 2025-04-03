<template>
	<div class="sidebar-header flex items-center justify-between gap-4">
		<div class="flex grow" :class="{ 'justify-center': logoMini }">
			<Logo
				v-if="logoMini"
				mini
				:dark="isDark"
				class="animate-[fade_calc(var(--sidebar-anim-duration)_*_2)_forwards_calc(var(--sidebar-anim-duration)_/_2)] opacity-0"
			/>
			<Logo
				v-if="!logoMini"
				:dark="isDark"
				class="animate-[fade_calc(var(--sidebar-anim-duration)_*_2)_forwards_calc(var(--sidebar-anim-duration)_/_2)] opacity-0"
			/>
		</div>
		<Transition name="fade" mode="out-in">
			<div v-if="showPin" class="sidebar-pin flex items-center">
				<Icon :size="20" @click="sidebarCollapsed = !sidebarCollapsed">
					<span class="i-large">
						<Iconify v-if="sidebarCollapsed" :icon="CircleRegular" />
						<Iconify v-if="!sidebarCollapsed" :icon="DotCircleRegular" />
					</span>
					<span class="i-small">
						<Iconify v-if="!sidebarCollapsed" :icon="CloseOutline" />
					</span>
				</Icon>
			</div>
		</Transition>
	</div>
</template>

<script lang="ts" setup>
import Logo from "@/app-layouts/common/Logo.vue"
import Icon from "@/components/common/Icon.vue"
import { useThemeStore } from "@/stores/theme"
import { Icon as Iconify } from "@iconify/vue"
import { computed } from "vue"

const { logoMini } = defineProps<{
	logoMini?: boolean
}>()

const CircleRegular = "fa6-regular:circle"
const DotCircleRegular = "fa6-regular:circle-dot"
const CloseOutline = "carbon:chevron-left"
const themeStore = useThemeStore()
const showPin = computed<boolean>(() => !logoMini)
const sidebarCollapsed = computed({
	get(): boolean {
		return themeStore.sidebar.collapsed
	},
	set() {
		themeStore.toggleSidebar()
	}
})
const isDark = computed<boolean>(() => themeStore.isThemeDark)
</script>

<style lang="scss" scoped>
@import "./variables";

.sidebar-header {
	height: var(--toolbar-height);
	min-height: var(--toolbar-height);

	.sidebar-pin {
		height: 100%;

		:deep() {
			.n-icon {
				cursor: pointer;

				.i-large {
					opacity: 0.3;
					transition: opacity var(--sidebar-anim-ease) var(--sidebar-anim-duration);
				}

				&:hover {
					opacity: 1;

					.i-large {
						opacity: 1;
					}
				}
			}
		}

		.i-large {
			display: block;
		}
		.i-small {
			display: none;
		}
		@media (max-width: $sidebar-bp) {
			.i-large {
				display: none;
			}
			.i-small {
				display: block;
			}
		}

		&.fade-enter-from,
		&.fade-leave-to {
			opacity: 0;
		}
	}
}

.direction-rtl {
	.sidebar-header {
		.sidebar-pin {
			.i-small {
				svg {
					transform: rotateY(180deg);
				}
			}
		}
	}
}
</style>
