<template>
	<nav class="nav" :class="[{ collapsed }, mode]">
		<n-menu
			ref="menu"
			v-model:value="selectedKey"
			:options="menuOptions"
			:collapsed
			:mode
			:indent="18"
			accordion
			:collapsed-width
			:dropdown-props="{
				scrollable: true,
				menuProps: () => ({
					class: 'main-nav'
				})
			}"
			:expanded-keys
			@update:expanded-keys="handleUpdateExpandedKeys"
		/>
	</nav>
</template>

<script lang="ts" setup>
import type { MenuInst } from "naive-ui"
import type { MenuMixedOption } from "naive-ui/es/menu/src/interface"
import type { RouteRecordNormalized } from "vue-router"
import _uniq from "lodash/uniq"
import { NMenu } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import { useRoute, useRouter } from "vue-router"
import { useThemeStore } from "@/stores/theme"
import getItems from "./items"

const { mode = "horizontal", collapsed = false } = defineProps<{
	mode?: "vertical" | "horizontal"
	collapsed?: boolean
}>()

const route = useRoute()
const router = useRouter()
const selectedKey = ref<string | null>(null)
const menu = ref<MenuInst | null>(null)
const expandedKeys = ref<string[] | undefined>(undefined)

const themeStore = useThemeStore()

const menuOptions = computed<MenuMixedOption[]>(() => getItems())
const collapsedWidth = computed<number>(() => themeStore.sidebar.closeWidth)
const sidebarCollapsed = computed<boolean>(() => themeStore.sidebar.collapsed)

function setMenuKey(matched: RouteRecordNormalized[]) {
	for (const match of matched) {
		if (match.name && typeof match.name === "string") {
			selectedKey.value = match.name?.toString() || null
			if (selectedKey.value) {
				menu.value?.showOption(selectedKey.value)
			}
		}
	}
}

onBeforeMount(() => {
	setMenuKey(route.matched)

	router.afterEach(route => {
		if (route?.matched?.length) {
			setMenuKey(route.matched)

			if (window.innerWidth <= 700 && !sidebarCollapsed.value) {
				themeStore.closeSidebar()
			}
		}
	})
})

// handler to simulate the accordion behavior in a specific submenu
function handleUpdateExpandedKeys(value: string[]) {
	const submenu = "components"

	if (value?.length && value.includes(submenu)) {
		const lastKey = value.pop()
		if (lastKey) {
			expandedKeys.value = _uniq([submenu, lastKey])
		}
	} else {
		expandedKeys.value = undefined
	}
}
</script>

<style lang="scss" scoped>
.nav {
	&.collapsed {
		pointer-events: none;
	}

	:deep() {
		.n-menu-item-group {
			.n-menu-item-group-title {
				white-space: nowrap;
				overflow: hidden;
				text-overflow: ellipsis;
			}
		}

		.n-submenu-children {
			--dash-width: 8px;
			--dash-height: 2px;
			--dash-offset: 29px;

			position: relative;

			&::before {
				content: "";
				display: block;
				background-color: var(--border-color);
				width: var(--dash-height);
				position: absolute;
				top: 0px;
				bottom: 20px;
				left: var(--dash-offset);
			}

			.n-menu-item-content {
				&::after {
					content: "";
					display: block;
					background-color: var(--border-color);
					width: var(--dash-width);
					height: var(--dash-height);
					position: absolute;
					z-index: -1;
					top: calc(50% - calc(ar(--dash-height) / 2));
					left: calc(var(--dash-offset) + var(--dash-height));
				}
			}

			.n-menu-item-group {
				.n-menu-item-group-title {
					padding-left: 44px !important;
				}
			}

			.n-submenu-children {
				&::before {
					display: none;
				}
				.n-menu-item-content {
					&::after {
						width: calc(var(--dash-width) * 3);
						background: repeating-linear-gradient(
							90deg,
							var(--border-color) 0px,
							var(--border-color) 5px,
							transparent 5px,
							transparent 8px
						);
					}
				}
			}
		}

		.n-menu--horizontal {
			.n-menu-item-content {
				.n-menu-item-content-header {
					overflow: initial;
				}
			}
		}
	}
}

.direction-rtl {
	.nav {
		:deep() {
			.n-submenu-children {
				--dash-offset: 25px;
			}
		}
	}
}
</style>
