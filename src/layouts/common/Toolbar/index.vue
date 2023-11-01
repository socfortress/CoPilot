<template>
	<header class="toolbar" :class="{ boxed }">
		<div class="wrap flex items-center justify-end gap-3">
			<Logo mini class="cursor-pointer" @click="openNav()" />

			<Breadcrumb class="grow" />
			<PinnedPages />

			<div class="bubble flex items-center">
				<Search />
				<LocaleSwitch />
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
import LocaleSwitch from "./LocaleSwitch.vue"
import FullscreenSwitch from "./FullscreenSwitch.vue"
import { useLoadingBar } from "naive-ui"
import { useRouter } from "vue-router"
import { useMainStore } from "@/stores/main"
import { useThemeStore } from "@/stores/theme"

const router = useRouter()

defineOptions({
	name: "Toolbar"
})

const props = defineProps<{
	boxed: boolean
}>()
const { boxed } = toRefs(props)

function openNav() {
	useThemeStore().openSidebar()
}

onMounted(() => {
	const loadingBar = useLoadingBar()
	router.beforeEach(() => loadingBar?.start())
	router.afterEach(() => loadingBar?.finish())
	useMainStore().setLoadingBar(loadingBar)
})
</script>

<style lang="scss" scoped>
.toolbar {
	position: sticky;
	top: 0;
	left: 0;
	backdrop-filter: blur(15px);
	height: var(--toolbar-height);
	// width: calc(100% - 1px);
	width: 100%;
	max-width: 100%;
	padding: 0 var(--view-padding);
	z-index: 3;
	//box-shadow: 0px 20px 20px 0px var(--bg-body);
	overflow: hidden;

	&::before {
		content: "";
		width: 100%;
		height: 100%;
		background-color: var(--bg-body);
		background: linear-gradient(var(--bg-body), rgba(255, 255, 255, 0) 100%);
		position: absolute;
		display: block;
		top: 0;
		left: 0;
		z-index: -1;
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

		@media (max-width: 1400px) {
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
		&::before {
			background-color: var(--bg-sidebar);
			background: linear-gradient(var(--bg-sidebar), rgba(255, 255, 255, 0) 100%);
		}
	}
}
</style>
