<template>
	<aside
		id="sidebar"
		class="sidebar flex flex-col"
		:class="{ collapsed: sidebarCollapsed, opened: !sidebarCollapsed }"
	>
		<div class="sidebar-wrap grow flex flex-col" ref="sidebar">
			<SidebarHeader :logo-mini="sidebarClosed" />
			<n-scrollbar>
				<Navbar :collapsed="sidebarClosed"></Navbar>
			</n-scrollbar>
			<SidebarFooter :collapsed="sidebarClosed" />
		</div>
	</aside>
</template>

<script lang="ts" setup>
import { computed, onMounted, ref, watch } from "vue"
import { NScrollbar } from "naive-ui"
import { isMobile } from "@/utils"
import { onClickOutside, useElementHover } from "@vueuse/core"
import Navbar from "@/layouts/common/Navbar/index.vue"
import SidebarHeader from "./SidebarHeader.vue"
import SidebarFooter from "./SidebarFooter.vue"
import { useThemeStore } from "@/stores/theme"

const themeStore = useThemeStore()
const sidebar = ref(null)
const sidebarHovered = useElementHover(sidebar)
const sidebarCollapsed = computed<boolean>(() => themeStore.sidebar.collapsed)
const sidebarClosed = computed<boolean>(() => !sidebarHovered.value && sidebarCollapsed.value)

function clickListener() {
	if (sidebar.value) {
		onClickOutside(sidebar, e => {
			if (!sidebarCollapsed.value) {
				e.stopPropagation()
				themeStore.closeSidebar()
			}
		})
	}
}
onMounted(() => {
	watch(
		sidebarCollapsed,
		val => {
			if (val) {
				if (isMobile()) {
					sidebarHovered.value = false
				}
			}
		},
		{
			immediate: true
		}
	)

	if (window.innerWidth <= 700) {
		clickListener()
	}
})
</script>

<style lang="scss" scoped>
@import "./variables";

.sidebar {
	position: fixed;
	z-index: 4;
	top: 0;
	left: 0;
	//bottom: 0;
	//border-right:var(--border-small-100);
	//padding-right: 1px;
	width: var(--sidebar-open-width);
	height: 100vh;
	height: 100svh;
	overflow-x: hidden;
	overflow-y: auto;
	background-color: var(--bg-sidebar);
	transition:
		width var(--sidebar-anim-ease) var(--sidebar-anim-duration),
		box-shadow var(--sidebar-anim-ease) var(--sidebar-anim-duration),
		color 0.3s var(--bezier-ease) 0s,
		background-color 0.3s var(--bezier-ease) 0s;
	z-index: -1;
	transition: all 0.3s var(--bezier-ease) 0s;
	transform: translateX(-100%);

	.sidebar-wrap {
		overflow: hidden;
	}

	@media (max-width: $sidebar-bp) {
		&.opened {
			z-index: 4;
			transform: translateX(0);
			box-shadow: 0px 0px 80px 0px rgba(0, 0, 0, 0.2);
		}
	}

	:deep(.n-scrollbar-rail) {
		opacity: 0.15;
	}
}

.direction-rtl {
	.sidebar {
		left: unset;
		right: 0;

		@media (max-width: $sidebar-bp) {
			transform: translateX(100%);

			&.opened {
				transform: translateX(0%);
			}
		}
	}
}
</style>
