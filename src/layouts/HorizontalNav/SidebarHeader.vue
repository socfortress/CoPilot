<template>
	<div class="sidebar-header flex items-center justify-between">
		<div class="logo-box grow" :class="{ mini: logoMini }">
			<Transition name="fade" mode="out-in">
				<Logo :mini="false" :dark="true" class="anim-wrap" v-if="isDark && !logoMini" />
				<Logo :mini="false" :dark="false" class="anim-wrap" v-else-if="isLight && !logoMini" />
				<Logo :mini="true" :dark="true" class="anim-wrap" v-else-if="isDark && logoMini" />
				<Logo :mini="true" :dark="false" class="anim-wrap" v-else-if="isLight && logoMini" />
			</Transition>
		</div>
		<Transition name="fade" mode="out-in">
			<div class="sidebar-pin flex items-center" v-if="showPin">
				<Icon :size="20" @click="sidebarCollapsed = !sidebarCollapsed">
					<span class="i-large">
						<Iconify :icon="CircleRegular" v-if="sidebarCollapsed" />
						<Iconify :icon="DotCircleRegular" v-if="!sidebarCollapsed" />
					</span>
					<span class="i-small">
						<Iconify :icon="CloseOutline" v-if="!sidebarCollapsed" />
					</span>
				</Icon>
			</div>
		</Transition>
	</div>
</template>

<script lang="ts" setup>
import { computed, toRefs } from "vue"
import { useThemeStore } from "@/stores/theme"
import Icon from "@/components/common/Icon.vue"
import { Icon as Iconify } from "@iconify/vue"
import Logo from "@/layouts/common/Logo.vue"

const CircleRegular = "fa6-regular:circle"
const DotCircleRegular = "fa6-regular:circle-dot"
const CloseOutline = "fa6-regular:circle-xmark"

const props = defineProps<{
	logoMini?: boolean
}>()
const { logoMini } = toRefs(props)

const showPin = computed<boolean>(() => !logoMini.value)
const sidebarCollapsed = computed({
	get(): boolean {
		return useThemeStore().sidebar.collapsed
	},
	set() {
		useThemeStore().toggleSidebar()
	}
})
const isDark = computed<boolean>(() => useThemeStore().isThemeDark)
const isLight = computed(() => useThemeStore().isThemeLight)
</script>

<style lang="scss" scoped>
@import "./variables";

.sidebar-header {
	height: var(--toolbar-height);
	min-height: var(--toolbar-height);

	:deep() {
		.logo-box {
			height: 100%;
			width: 100%;
			position: relative;

			.anim-wrap {
				padding: 16px 0px;
				position: absolute;
				top: 0;
				left: 0;
				right: 0;
				bottom: 0;
				display: flex;
				align-items: center;

				img {
					max-height: 32px;
					display: block;
					height: calc(var(--toolbar-height) - 32px);
					transform: translateX(32px);
					transition: transform var(--sidebar-anim-ease) var(--sidebar-anim-duration);
				}
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

		&.mini {
			width: 100%;
			.anim-wrap {
				img {
					transform: translateX(22px);
				}
			}
		}
	}

	.sidebar-pin {
		padding-right: 16px;
		height: 100%;

		:deep() {
			.n-icon {
				cursor: pointer;
				opacity: 0.3;
				transition: opacity var(--sidebar-anim-ease) var(--sidebar-anim-duration);

				&:hover {
					opacity: 1;
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
</style>
