<template>
	<div id="main" class="main" :class="{ 'sidebar-collapsed': sidebarCollapsed, 'sidebar-opened': !sidebarCollapsed }">
		<n-scrollbar ref="scrollbar">
			<Toolbar :boxed="toolbarBoxed" class="gradient-bg-sidebar" />
			<div class="view" :class="[{ boxed }, `route-${routeName}`]">
				<slot></slot>
			</div>
			<FooterEL :boxed="boxed" v-if="footerShown" />
		</n-scrollbar>
	</div>
</template>

<script lang="ts" setup>
import { computed, ref, onMounted } from "vue"
import { NScrollbar } from "naive-ui"
import { useRoute, useRouter } from "vue-router"
import Toolbar from "@/layouts/common/Toolbar/index.vue"
import FooterEL from "@/layouts/common/FooterEL.vue"
import { useThemeStore } from "@/stores/theme"

defineOptions({
	name: "MainContainer"
})

const router = useRouter()
const route = useRoute()
const routeName = computed<string>(() => route.name?.toString() || "")
const sidebarCollapsed = computed<boolean>(() => useThemeStore().sidebar.collapsed)
const footerShown = computed(() => useThemeStore().isFooterShown)
const boxed = computed<boolean>(() => useThemeStore().isBoxed)
const toolbarBoxed = computed(() => useThemeStore().isToolbarBoxed)
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
		}
	}

	.view {
		padding: var(--view-padding);
		padding-top: 0;

		&.boxed {
			max-width: var(--boxed-width);
			margin: 0 auto;
		}
	}

	@media (max-width: $sidebar-bp) {
		padding-left: 0px;
		&.sidebar-collapsed {
			padding-left: 0px;
		}

		transition: all var(--sidebar-anim-ease) var(--sidebar-anim-duration);

		&.sidebar-opened {
			//transform: scale(0.8) translateX(100%) rotateY(35deg);
			transform-origin: center left;
			border-radius: 16px;
			overflow: hidden;
			opacity: 0.5;
		}
	}

	@media (min-width: ($sidebar-bp + 1px)) {
		:deep() {
			header.toolbar {
				.logo {
					display: none;
				}
			}
		}
	}
}
</style>
