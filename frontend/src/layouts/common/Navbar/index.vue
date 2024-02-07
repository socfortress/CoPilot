<template>
	<nav class="nav" :class="[{ collapsed }, mode]">
		<n-menu
			ref="menu"
			:options="menuOptions"
			:collapsed="collapsed"
			:mode="mode"
			:accordion="true"
			:collapsed-width="collapsedWidth"
			:dropdown-props="{
				scrollable: true,
				menuProps: () => ({
					class: 'main-nav'
				})
			}"
			v-model:value="selectedKey"
			:expanded-keys="expandedKeys"
			@update:expanded-keys="handleUpdateExpandedKeys"
		/>
	</nav>
</template>

<script lang="ts" setup>
import { type MenuInst, NMenu } from "naive-ui"
import getItems from "./items"
import { useThemeStore } from "@/stores/theme"
import { type MenuMixedOption } from "naive-ui/es/menu/src/interface"
import { computed, onBeforeMount, ref, toRefs } from "vue"
import { useRouter, useRoute, type RouteRecordNormalized } from "vue-router"
import _uniq from "lodash/uniq"

defineOptions({
	name: "Navbar"
})

const route = useRoute()
const router = useRouter()

const props = withDefaults(
	defineProps<{
		mode?: "vertical" | "horizontal"
		collapsed?: boolean
	}>(),
	{ mode: "vertical", collapsed: false }
)
const { mode, collapsed } = toRefs(props)

const selectedKey = ref<string | null>(null)
const menu = ref<MenuInst | null>(null)
const expandedKeys = ref<string[] | undefined>(undefined)

const menuOptions = computed<MenuMixedOption[]>(() => getItems(mode.value, collapsed.value))
const collapsedWidth = computed<number>(() => useThemeStore().sidebar.closeWidth)
const sidebarCollapsed = computed<boolean>(() => useThemeStore().sidebar.collapsed)

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
				useThemeStore().closeSidebar()
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
		.n-menu-item-content,
		.n-menu-item-group {
			.item-badge {
				display: flex;
				justify-content: space-between;
				align-items: center;
				gap: 10px;

				:nth-child(1) {
					overflow: hidden;
					white-space: nowrap;
					text-overflow: ellipsis;
				}

				:nth-child(2) {
					color: var(--fg-color);
					background: var(--hover-005-color);
					margin-right: 10px;
					height: 22px;
					line-height: 24px;
					border-radius: 15px;
					padding: 0 7px;
					font-weight: bold;
					font-size: 13px;
					font-family: var(--font-family-mono);
				}
			}

			&.n-menu-item-content--selected,
			&.n-menu-item-content--child-active {
				.item-badge {
					:nth-child(2) {
						color: var(--n-item-text-color-active);
						background: var(--n-item-color-active);
					}
				}
			}
		}

		.n-menu-item-group {
			.n-menu-item-group-title {
				white-space: nowrap;
				overflow: hidden;
				text-overflow: ellipsis;
			}
			.item-badge {
				:nth-child(2) {
					font-size: 10px;
					margin-right: 0px;
					height: 20px;
					line-height: 20px;
					border-radius: 8px;
					padding: 0 6px;
				}
			}
		}

		.n-submenu-children {
			.n-menu-item-content {
				&::after {
					content: "";
					display: block;
					opacity: 0.1;
					background-color: var(--fg-color);
					width: 12px;
					height: 2px;
					position: absolute;
					top: 50%;
					left: 38px;
					margin-top: -1px;
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
</style>

<style lang="scss">
.main-nav {
	.n-dropdown-option-body,
	.n-dropdown-option-body--group,
	.n-dropdown-option-body__label {
		.item-badge {
			display: flex;
			justify-content: space-between;
			align-items: center;
			gap: 12px;

			:nth-child(1) {
				overflow: hidden;
				white-space: nowrap;
				text-overflow: ellipsis;
			}

			:nth-child(2) {
				color: var(--fg-color);
				background: var(--hover-005-color);
				font-weight: bold;
				font-family: var(--font-family-mono);
				font-size: 10px;
				margin-right: 0px;
				height: 20px;
				line-height: 20px;
				border-radius: 8px;
				padding: 0 6px;
			}
		}

		&.n-dropdown-option-body--selected,
		&.n-dropdown-option-body--child-active {
			.item-badge {
				:nth-child(2) {
					color: var(--n-item-text-color-active);
					background: var(--primary-010-color);
				}
			}
		}
	}
}
</style>
