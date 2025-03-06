<template>
	<n-split
		ref="splitPane"
		direction="horizontal"
		:default-size="sanitizedDefaultSplit"
		:min="0"
		:max="1"
		:resize-trigger-size="0"
		:disabled="!enableResize || splitDisabled"
		class="wrapper flex grow"
		:class="[{ 'sidebar-open': sidebarOpen }, `sidebar-position-${sidebarPosition}`]"
		:pane1-style="pane1Style"
	>
		<template #[tplNameSide]>
			<div v-if="sidebarAvailable" ref="sidebar" class="sidebar flex flex-col">
				<div v-if="$slots['sidebar-header']" class="sidebar-header flex items-center justify-between">
					<slot name="sidebar-header" />
					<n-button text class="close-btn" @click="sidebarOpen = false">
						<Icon :size="24" :name="CloseIcon" />
					</n-button>
				</div>
				<div v-if="$slots['sidebar-content']" class="sidebar-main grow">
					<n-scrollbar class="max-h-full">
						<div class="sidebar-main-content" :style="sidebarContentStyle" :class="sidebarContentClass">
							<slot name="sidebar-content" />
						</div>
					</n-scrollbar>
				</div>
				<div v-if="$slots['sidebar-footer']" class="sidebar-footer flex items-center">
					<slot name="sidebar-footer" />
				</div>
			</div>
		</template>

		<template #resize-trigger>
			<div class="split-trigger">
				<div class="split-trigger-icon">
					<Icon :name="SplitIcon" :size="12" />
				</div>
			</div>
		</template>

		<template #[tplNameMain]>
			<div class="main flex flex-grow flex-col">
				<div v-if="$slots['main-toolbar']" class="main-toolbar flex items-center">
					<div v-if="sidebarAvailable && !hideMenuBtn" class="menu-btn flex justify-center opacity-50">
						<n-button text @click="sidebarOpen = true">
							<Icon :size="24" :name="MenuIcon" />
						</n-button>
					</div>

					<div class="grow">
						<slot name="main-toolbar" />
					</div>
				</div>
				<div class="main-view grow" :class="{ 'no-container-query': disableContainerQuery }">
					<n-scrollbar v-if="useMainScroll" ref="mainScrollbar" class="max-h-full">
						<div class="main-content" :style="mainContentStyle" :class="mainContentClass">
							<slot name="main-content" />
						</div>
					</n-scrollbar>
					<div v-else class="main-content" :style="mainContentStyle" :class="mainContentClass">
						<slot name="main-content" />
					</div>
				</div>
				<div v-if="$slots['main-footer']" class="main-footer flex items-center">
					<div class="wrap">
						<slot name="main-footer" />
					</div>
				</div>

				<div v-if="sidebarOpen" class="main-overlay" />
			</div>
		</template>
	</n-split>
</template>

<script setup lang="ts">
import type { SetupContext } from "vue"
import Icon from "@/components/common/Icon.vue"
import { onClickOutside, useWindowSize } from "@vueuse/core"
import { NButton, NScrollbar, NSplit } from "naive-ui"
import { computed, onMounted, ref, useSlots, watch } from "vue"

type SidebarPosition = "left" | "right"

export interface CtxSegmentedPage {
	mainScrollbar: typeof NScrollbar | null
	closeSidebar: () => void
	openSidebar: () => void
}

const {
	hideMenuBtn,
	mainContentStyle,
	mainContentClass,
	sidebarContentStyle,
	sidebarContentClass,
	enableResize,
	disableContainerQuery,
	sidebarPosition = "left",
	useMainScroll = true,
	defaultSplit = 0.3,
	maxSidebarWidth = 450,
	minSidebarWidth = 250,
	padding = "30px",
	paddingMobile = "20px",
	toolbarHeight = "70px",
	toolbarHeightMobile = "62px"
} = defineProps<{
	sidebarPosition?: SidebarPosition
	hideMenuBtn?: boolean
	useMainScroll?: boolean
	mainContentStyle?: string
	mainContentClass?: string
	sidebarContentStyle?: string
	sidebarContentClass?: string
	enableResize?: boolean
	disableContainerQuery?: boolean
	defaultSplit?: number
	maxSidebarWidth?: number
	minSidebarWidth?: number
	padding?: string
	paddingMobile?: string
	toolbarHeight?: string
	toolbarHeightMobile?: string
}>()

const emit = defineEmits<{
	(e: "mounted", value: CtxSegmentedPage): void
	(e: "sidebar", value: boolean): void
}>()

const MenuIcon = "ph:list-light"
const CloseIcon = "carbon:close"
const SplitIcon = "carbon:draggable"

const splitPane = ref()
const sanitizedDefaultSplit = ref(defaultSplit)
const splitDisabled = ref(false)

const slots: SetupContext["slots"] = useSlots()
const sidebarOpen = ref(false)
const sidebar = ref(null)
const mainScrollbar = ref<typeof NScrollbar | null>(null)
const { width } = useWindowSize()
const sidebarAvailable = computed<boolean>(
	() => !!slots["sidebar-header"] || !!slots["sidebar-content"] || !!slots["sidebar-footer"]
)
const isSidebarLeft = computed<boolean>(() => sidebarPosition === "left")
const tplNameMain = computed<1 | 2>(() => (isSidebarLeft.value ? 2 : 1))
const tplNameSide = computed<1 | 2>(() => (isSidebarLeft.value ? 1 : 2))
const pane1Style = computed(() => ({
	maxWidth: isSidebarLeft.value ? `${maxSidebarWidth}px` : `calc(100% - ${minSidebarWidth}px)`,
	minWidth: isSidebarLeft.value ? `${minSidebarWidth}px` : `calc(100% - ${maxSidebarWidth}px)`
}))

function closeSidebar() {
	sidebarOpen.value = false
}

function openSidebar() {
	sidebarOpen.value = true
}

onClickOutside(sidebar, () => closeSidebar())

watch(
	sidebarOpen,
	val => {
		emit("sidebar", val)
	},
	{ immediate: true }
)

watch(
	width,
	val => {
		sanitizedDefaultSplit.value = val <= 700 ? 0 : isSidebarLeft.value ? defaultSplit : 1 - defaultSplit
		splitDisabled.value = val <= 700
	},
	{ immediate: true }
)

onMounted(() => {
	emit("mounted", {
		mainScrollbar: mainScrollbar.value,
		closeSidebar,
		openSidebar
	})
})
</script>

<style lang="scss" scoped>
.wrapper {
	--mb-toolbar-height: v-bind(toolbarHeight);
	--padding-x: v-bind(padding);
	position: relative;
	height: 100%;
	overflow: hidden;
	border-radius: var(--border-radius);
	border: 1px solid var(--border-color);
	background-color: var(--bg-default-color);
	direction: ltr;

	.split-trigger {
		height: 100%;
		width: 3px;
		display: flex;
		align-items: center;
		position: relative;
		z-index: 1;
		left: -2px;
		transition: background-color 0.3s var(--bezier-ease);

		.split-trigger-icon {
			background-color: var(--border-color);
			border-radius: var(--border-radius-small);
			height: 18px;
			display: flex;
			justify-content: center;
			align-items: center;
			position: relative;
			margin-left: -5px;
			z-index: 1;
			transition: background-color 0.3s var(--bezier-ease);
		}

		&:hover {
			background-color: rgba(var(--primary-color-rgb) / 0.1);

			.split-trigger-icon {
				background-color: rgba(var(--primary-color-rgb) / 0.1);
			}
		}
	}

	.sidebar {
		background-color: var(--bg-secondary-color);
		height: 100%;
		overflow: hidden;
		border-right: 1px solid var(--border-color);

		.sidebar-header {
			border-block-end: 1px solid var(--border-color);
			min-height: var(--mb-toolbar-height);
			height: var(--mb-toolbar-height);
			padding: 0 var(--padding-x);

			.close-btn {
				display: none;
			}
		}

		.sidebar-main {
			overflow: hidden;

			.sidebar-main-content {
				padding: var(--padding-x);
			}
		}

		.sidebar-footer {
			border-block-start: 1px solid var(--border-color);
			min-height: var(--mb-toolbar-height);
			padding: 0 var(--padding-x);
		}
	}

	.main {
		background-color: var(--bg-default-color);
		position: relative;
		height: 100%;

		.main-overlay {
			position: absolute;
			width: 100%;
			height: 100%;
			z-index: 2;
			top: 0;
			left: 0;
		}

		.main-toolbar {
			border-block-end: 1px solid var(--border-color);
			min-height: var(--mb-toolbar-height);
			height: var(--mb-toolbar-height);
			padding: 0 var(--padding-x);
			gap: 18px;
			line-height: 1.3;
			container-type: inline-size;

			.menu-btn {
				display: none;
			}
		}

		.main-view {
			overflow: hidden;
			&:not(.no-container-query) {
				container-type: inline-size;
			}

			.main-content {
				padding: var(--padding-x);
			}
		}

		.main-footer {
			container-type: inline-size;
			border-block-start: 1px solid var(--border-color);
			padding: 0 var(--padding-x);

			.wrap {
				min-height: calc(var(--mb-toolbar-height) - 1px);
				width: 100%;
				display: flex;
				align-items: center;
			}
		}
	}

	&.sidebar-position-right {
		.sidebar {
			border-right: none;
			border-left: 1px solid var(--border-color);
		}
	}

	@media (max-width: 700px) {
		--mb-toolbar-height: v-bind(toolbarHeightMobile);
		--padding-x: v-bind(paddingMobile);

		height: 100%;
		overflow: hidden;
		border-radius: 0;
		border: none;

		&::before {
			content: "";
			width: 100vw;
			display: block;
			background-color: var(--bg-body-color);
			position: absolute;
			top: 0;
			left: 0;
			bottom: 0;
			transform: translateX(-100%);
			opacity: 0;
			transition:
				opacity 0.25s ease-in-out,
				transform 0s linear 0.3s;
			z-index: 1;
		}

		.sidebar {
			position: absolute;
			top: 0;
			left: 0;
			bottom: 0;
			transform: translateX(-100%);
			transition: transform 0.25s ease-in-out;
			z-index: 3;
			min-width: 300px;
			max-width: min(450px, 80vw);

			&::before {
				content: "";
				width: 100%;
				height: 100%;
				display: block;
				background-color: var(--bg-default-color);
				z-index: -1;
				position: absolute;
			}

			.sidebar-header,
			.sidebar-footer {
				padding: 0 var(--padding-x);

				.close-btn {
					display: flex;
				}
			}

			.sidebar-main {
				.sidebar-main-content {
					padding: var(--padding-x);
				}
			}
		}
		.main {
			.main-toolbar {
				padding: 0 var(--padding-x);
				gap: 14px;

				.menu-btn {
					display: flex;
				}
			}

			.main-view {
				.main-content {
					padding: var(--padding-x);
				}
			}
			.main-footer {
				padding: 0 var(--padding-x);
			}
		}

		&.sidebar-position-left {
			:deep() {
				.n-split-pane-1 {
					min-width: 0 !important;
					max-width: 0 !important;
				}
			}
		}

		&.sidebar-position-right {
			:deep() {
				.n-split-pane-1 {
					min-width: 100% !important;
					max-width: 100% !important;
				}
			}

			&::before,
			.sidebar {
				left: initial;
				right: 0;
				transform: translateX(100%);
			}

			.main {
				.main-toolbar {
					flex-direction: row-reverse;
					justify-content: space-between;
				}
			}
		}

		&.sidebar-open {
			&::before {
				transform: translateX(0);
				opacity: 0.4;
				transition:
					opacity 0.25s ease-in-out,
					transform 0s linear 0s;
			}

			.sidebar {
				transform: translateX(0);
				box-shadow: 0px 0px 80px 0px rgba(0, 0, 0, 0.1);
			}
		}
	}
}

.direction-rtl {
	.wrapper {
		.sidebar,
		.main {
			direction: rtl;
		}
	}
}
</style>
