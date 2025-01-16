<template>
	<div
		id="app-main"
		class="main"
		:class="{ 'sidebar-collapsed': sidebarCollapsed, 'sidebar-opened': !sidebarCollapsed }"
	>
		<n-scrollbar
			ref="scrollbar"
			trigger="none"
			:y-placement="isRTL ? 'left' : 'right'"
			content-class="min-h-full flex flex-col"
			:theme-overrides="{
				railInsetVerticalRight: `${toolbarHeight}px 4px 4px auto`,
				railInsetVerticalLeft: `${toolbarHeight}px auto 4px 4px`
			}"
		>
			<Toolbar :boxed="toolbarBoxed" class="gradient-bg-sidebar" />
			<div
				id="app-view"
				class="view"
				:class="{ boxed, 'view-padded': overridePadded === true, 'view-no-padded': overridePadded === false }"
			>
				<slot />
			</div>
			<MainFooter v-if="footerShown" :boxed />
		</n-scrollbar>
	</div>
</template>

<script lang="ts" setup>
import MainFooter from "@/app-layouts/common/MainFooter.vue"
import Toolbar from "@/app-layouts/common/Toolbar"
import { useThemeStore } from "@/stores/theme"
import { NScrollbar } from "naive-ui"
import { computed, onMounted, ref } from "vue"
import { type RouteLocationNormalizedGeneric, useRoute, useRouter } from "vue-router"

const themeStore = useThemeStore()
const router = useRouter()
const route = useRoute()
const sidebarCollapsed = computed<boolean>(() => themeStore.sidebar.collapsed)
const footerShown = computed(() => themeStore.isFooterShown)
const themeBoxed = computed<boolean>(() => themeStore.isBoxed)
const overrideBoxed = ref<boolean | undefined>(undefined)
const overridePadded = ref<boolean | undefined>(undefined)
const boxed = computed<boolean>(() => (overrideBoxed.value !== undefined ? overrideBoxed.value : themeBoxed.value))
const isRTL = computed<boolean>(() => themeStore.isRTL)
const toolbarBoxed = computed(() => themeStore.isToolbarBoxed)
const toolbarHeight = computed(() => themeStore.toolbarHeight)
const scrollbar = ref()

function checkThemeOverrides(currentRoute: RouteLocationNormalizedGeneric) {
	if (currentRoute.meta?.theme?.boxed?.enabled !== undefined) {
		overrideBoxed.value = currentRoute.meta.theme.boxed.enabled
	} else {
		overrideBoxed.value = undefined
	}

	if (currentRoute.meta?.theme?.padded?.enabled !== undefined) {
		overridePadded.value = currentRoute.meta.theme.padded.enabled
	} else {
		overridePadded.value = undefined
	}
}

router.beforeEach(checkThemeOverrides)

onMounted(() => {
	checkThemeOverrides(route)

	router.afterEach(() => {
		if (scrollbar?.value?.scrollTo) {
			scrollbar?.value.scrollTo({ top: 0, behavior: "smooth" })
		}
	})
})
</script>

<style lang="scss" scoped>
@import "./variables";

.main {
	width: 100%;
	overflow: hidden;
	background-color: var(--bg-body-color);
	transition: all var(--sidebar-anim-ease) var(--sidebar-anim-duration);

	.view {
		padding: 0 var(--view-padding);
		flex-grow: 1;
		width: 100%;
		margin: 0 auto;

		&.boxed {
			max-width: var(--boxed-width);
		}
		&.view-no-padded {
			padding: 0;
		}
	}

	@media (max-width: $sidebar-bp) {
		&.sidebar-opened {
			/*
			transform: scale(0.8) translateX(100%) rotateY(35deg);
			transform-origin: center left;
			border-radius: 16px;
			*/

			overflow: hidden;
			opacity: 0.5;
		}
	}

	@media (min-width: ($sidebar-bp + 1px)) {
		:deep() {
			header.toolbar {
				.logo-box {
					display: none;
				}
			}
		}
	}
}
</style>
