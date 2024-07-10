<template>
	<div id="main" class="main" :class="{ 'sidebar-collapsed': sidebarCollapsed, 'sidebar-opened': !sidebarCollapsed }">
		<n-scrollbar ref="scrollbar">
			<Toolbar :boxed="toolbarBoxed" class="gradient-bg-sidebar" />
			<div class="view" :class="[{ boxed }, `route-${routeName}`]">
				<slot></slot>
			</div>
			<MainFooter :boxed="boxed" v-if="footerShown" />
		</n-scrollbar>
	</div>
</template>

<script lang="ts" setup>
import { computed, ref, onMounted } from "vue"
import { NScrollbar } from "naive-ui"
import { useRoute, useRouter } from "vue-router"
import Toolbar from "@/layouts/common/Toolbar/index.vue"
import MainFooter from "@/layouts/common/MainFooter.vue"
import { useThemeStore } from "@/stores/theme"

const themeStore = useThemeStore()
const router = useRouter()
const route = useRoute()
const routeName = computed<string>(() => route.name?.toString() || "")
const sidebarCollapsed = computed<boolean>(() => themeStore.sidebar.collapsed)
const footerShown = computed(() => themeStore.isFooterShown)
const boxed = computed<boolean>(() => themeStore.isBoxed)
const toolbarBoxed = computed(() => themeStore.isToolbarBoxed)
const scrollbar = ref()

onMounted(() => {
	router.afterEach(() => {
		if (scrollbar?.value?.scrollTo) {
			scrollbar?.value.scrollTo({ top: 0 })
		}
	})
})
</script>

<style lang="scss" scoped>
@import "./variables";

.main {
	width: 100%;
	height: 100%;
	overflow: hidden;
	position: relative;
	transition: padding var(--sidebar-anim-ease) var(--sidebar-anim-duration);
	background-color: var(--bg-body);

	:deep() {
		& > .n-scrollbar {
			& > .n-scrollbar-rail {
				top: calc(var(--toolbar-height) + 2px);
			}

			& > .n-scrollbar-container {
				& > .n-scrollbar-content {
					min-height: 100%;
					display: flex;
					flex-direction: column;
				}
			}
		}
	}

	.view {
		padding: var(--view-padding);
		padding-top: 0;
		flex-grow: 1;
		width: 100%;
		display: flex;
		flex-direction: column;

		&.boxed {
			max-width: var(--boxed-width);
			margin: 0 auto;
		}
	}

	@media (max-width: $sidebar-bp) {
		transition: all var(--sidebar-anim-ease) var(--sidebar-anim-duration);

		.view {
			padding-top: calc(var(--view-padding) / 2);
		}

		&.sidebar-opened {
			//transform: scale(0.8) translateX(100%) rotateY(35deg);
			//transform-origin: center left;
			//border-radius: 16px;
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
