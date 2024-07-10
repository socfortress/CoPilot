<template>
	<header class="toolbar" :class="{ boxed }">
		<div class="wrap flex items-center justify-end gap-3">
			<div class="logo-box flex items-center gap-2 cursor-pointer" @click="openNav()">
				<Logo mini />
				<Icon :size="20" name="carbon:chevron-right"></Icon>
			</div>

			<Breadcrumb class="grow" />
			<PinnedPages />

			<div class="bubble flex items-center">
				<Search />
				<FullscreenSwitch />
				<ThemeSwitch />
				<Notifications />
				<Avatar />
			</div>
		</div>
	</header>
</template>

<script lang="ts" setup>
import { onMounted, toRefs } from "vue"
import Logo from "../Logo.vue"
import Breadcrumb from "./Breadcrumb.vue"
import Avatar from "./Avatar.vue"
import Search from "./Search.vue"
import PinnedPages from "./PinnedPages.vue"
import ThemeSwitch from "./ThemeSwitch.vue"
import Notifications from "./Notifications.vue"
import FullscreenSwitch from "./FullscreenSwitch.vue"
import Icon from "@/components/common/Icon.vue"
import { useLoadingBar } from "naive-ui"
import { useRouter } from "vue-router"
import { useMainStore } from "@/stores/main"
import { useThemeStore } from "@/stores/theme"

const props = defineProps<{
	boxed: boolean
}>()
const { boxed } = toRefs(props)

const router = useRouter()
const themeStore = useThemeStore()
const mainStore = useMainStore()

function openNav() {
	themeStore.openSidebar()
}

onMounted(() => {
	const loadingBar = useLoadingBar()
	router.beforeEach(() => loadingBar?.start())
	router.afterEach(() => loadingBar?.finish())
	mainStore.setLoadingBar(loadingBar)
})
</script>

<style lang="scss" scoped>
@import "@/assets/scss/functions.scss";

.toolbar {
	position: sticky;
	top: 0;
	left: 0;
	height: var(--toolbar-height);
	width: 100%;
	max-width: 100%;
	padding: 0 var(--view-padding);
	z-index: 3;
	overflow: hidden;
	background: var(--bg-body);

	&::before {
		content: "";
		width: 100%;
		height: 100%;
		position: absolute;
		display: block;
		top: 0;
		left: 0;
		z-index: -1;
		backdrop-filter: blur(20px);
		// mask-image: scrimGradient(#000);
		mask-image: linear-gradient(
			to bottom,
			hsl(0, 0%, 0%) 0%,
			hsla(0, 0%, 0%, 0.979) 0.6%,
			hsla(0, 0%, 0%, 0.962) 2.2%,
			hsla(0, 0%, 0%, 0.946) 4.9%,
			hsla(0, 0%, 0%, 0.929) 8.6%,
			hsla(0, 0%, 0%, 0.91) 13.3%,
			hsla(0, 0%, 0%, 0.884) 18.8%,
			hsla(0, 0%, 0%, 0.851) 25.1%,
			hsla(0, 0%, 0%, 0.806) 32.3%,
			hsla(0, 0%, 0%, 0.749) 40.2%,
			hsla(0, 0%, 0%, 0.677) 48.7%,
			hsla(0, 0%, 0%, 0.587) 57.9%,
			hsla(0, 0%, 0%, 0.476) 67.7%,
			hsla(0, 0%, 0%, 0.343) 78%,
			hsla(0, 0%, 0%, 0.185) 88.8%,
			hsla(0, 0%, 0%, 0) 100%
		);
	}

	.wrap {
		height: var(--toolbar-height);
		overflow: hidden;
		width: 100%;
		max-width: 100%;

		.bubble {
			background-color: var(--bg-sidebar);
			color: var(--fg-color);
			border-radius: 50px;
			padding: 6px;
			transition: all 0.3s;
			gap: 14px;
		}

		@media (max-width: 850px) {
			.pinned-pages {
				display: none;
			}
		}

		@media (max-width: 700px) {
			justify-content: space-between;
			.breadcrumb {
				display: none;
			}
		}
	}

	&.boxed {
		padding: 0;
		.wrap {
			padding: 0 var(--view-padding);
			max-width: var(--boxed-width);
			margin: 0 auto;
		}
	}

	&.gradient-bg-sidebar {
		background-color: var(--bg-sidebar);
		background: linear-gradient(
			to bottom,
			rgba(var(--bg-sidebar-rgb), 1) 0%,
			rgba(var(--bg-sidebar-rgb), 0.945) 8.6%,
			rgba(var(--bg-sidebar-rgb), 0.888) 16.2%,
			rgba(var(--bg-sidebar-rgb), 0.83) 22.9%,
			rgba(var(--bg-sidebar-rgb), 0.769) 28.9%,
			rgba(var(--bg-sidebar-rgb), 0.707) 34.4%,
			rgba(var(--bg-sidebar-rgb), 0.644) 39.5%,
			rgba(var(--bg-sidebar-rgb), 0.578) 44.5%,
			rgba(var(--bg-sidebar-rgb), 0.511) 49.5%,
			rgba(var(--bg-sidebar-rgb), 0.443) 54.7%,
			rgba(var(--bg-sidebar-rgb), 0.373) 60.3%,
			rgba(var(--bg-sidebar-rgb), 0.301) 66.4%,
			rgba(var(--bg-sidebar-rgb), 0.228) 73.3%,
			rgba(var(--bg-sidebar-rgb), 0.153) 81%,
			rgba(var(--bg-sidebar-rgb), 0.077) 89.9%,
			rgba(var(--bg-sidebar-rgb), 0) 100%
		);
	}
	&.gradient-bg-body {
		background-color: var(--bg-body);
		background: linear-gradient(
			to bottom,
			rgba(var(--bg-body-rgb), 1) 0%,
			rgba(var(--bg-body-rgb), 0.738) 19%,
			rgba(var(--bg-body-rgb), 0.541) 34%,
			rgba(var(--bg-body-rgb), 0.382) 47%,
			rgba(var(--bg-body-rgb), 0.278) 56.5%,
			rgba(var(--bg-body-rgb), 0.194) 65%,
			rgba(var(--bg-body-rgb), 0.126) 73%,
			rgba(var(--bg-body-rgb), 0.075) 80.2%,
			rgba(var(--bg-body-rgb), 0.042) 86.1%,
			rgba(var(--bg-body-rgb), 0.021) 91%,
			rgba(var(--bg-body-rgb), 0.008) 95.2%,
			rgba(var(--bg-body-rgb), 0.002) 98.2%,
			rgba(var(--bg-body-rgb), 0) 100%
		);
	}
}

.direction-rtl {
	.toolbar {
		.wrap {
			.logo-box {
				.n-icon {
					transform: rotateY(180deg);
				}
			}
		}
	}
}
</style>
