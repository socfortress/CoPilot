<template>
	<n-split
		direction="horizontal"
		:default-size="splitDefault"
		:min="0"
		:max="1"
		:resize-trigger-size="0"
		:disabled="!enableResize || splitDisabled"
		ref="splitPane"
		class="wrapper flex grow"
		:class="[{ 'sidebar-open': sidebarOpen }, `sidebar-position-${sidebarPosition}`]"
	>
		<template #1>
			<div class="sidebar flex flex-col" ref="sidebar" v-if="sidebarAvailable">
				<div class="sidebar-header flex items-center" v-if="$slots['sidebar-header']">
					<slot name="sidebar-header"></slot>
				</div>
				<div class="sidebar-main grow" v-if="$slots['sidebar-content']">
					<n-scrollbar class="max-h-full">
						<div class="sidebar-main-content" :style="sidebarContentStyle" :class="sidebarContentClass">
							<slot name="sidebar-content"></slot>
						</div>
					</n-scrollbar>
				</div>
				<div class="sidebar-footer flex items-center" v-if="$slots['sidebar-footer']">
					<slot name="sidebar-footer"></slot>
				</div>
			</div>
		</template>

		<template #resize-trigger>
			<div class="split-trigger">
				<div class="split-trigger-icon">
					<Icon :name="SplitIcon" :size="12"></Icon>
				</div>
			</div>
		</template>

		<template #2>
			<div class="main flex-grow flex flex-col">
				<div class="main-toolbar flex items-center" v-if="$slots['main-toolbar']">
					<div class="menu-btn flex justify-center opacity-50" v-if="sidebarAvailable && !hideMenuBtn">
						<n-button text @click="sidebarOpen = true">
							<Icon :size="24" :name="MenuIcon"></Icon>
						</n-button>
					</div>

					<div class="grow">
						<slot name="main-toolbar"></slot>
					</div>
				</div>
				<div class="main-view grow" :class="{ 'no-container-query': disableContainerQuery }">
					<n-scrollbar class="max-h-full" v-if="useMainScroll" ref="mainScrollbar">
						<div class="main-content" :style="mainContentStyle" :class="mainContentClass">
							<slot name="main-content"></slot>
						</div>
					</n-scrollbar>
					<div class="main-content" :style="mainContentStyle" :class="mainContentClass" v-else>
						<slot name="main-content"></slot>
					</div>
				</div>
				<div class="main-footer flex items-center" v-if="$slots['main-footer']">
					<div class="wrap">
						<slot name="main-footer"></slot>
					</div>
				</div>

				<div class="main-overlay" v-if="sidebarOpen"></div>
			</div>
		</template>
	</n-split>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, toRefs, useSlots, watch } from "vue"
import { NScrollbar, NButton, NSplit } from "naive-ui"
import { onClickOutside, useWindowSize } from "@vueuse/core"
import Icon from "@/components/common/Icon.vue"

type SidebarPosition = "left" | "right"

export interface CtxSegmentedPage {
	mainScrollbar: typeof NScrollbar | null
	closeSidebar: () => void
	openSidebar: () => void
}

const emit = defineEmits<{
	(e: "mounted", value: CtxSegmentedPage): void
	(e: "sidebar", value: boolean): void
}>()

const props = withDefaults(
	defineProps<{
		sidebarPosition?: SidebarPosition
		hideMenuBtn?: boolean
		useMainScroll?: boolean
		mainContentStyle?: string
		mainContentClass?: string
		sidebarContentStyle?: string
		sidebarContentClass?: string
		enableResize?: boolean
		disableContainerQuery?: boolean
	}>(),
	{ sidebarPosition: "left", useMainScroll: true }
)
const {
	sidebarPosition,
	hideMenuBtn,
	useMainScroll,
	mainContentStyle,
	mainContentClass,
	sidebarContentStyle,
	sidebarContentClass
} = toRefs(props)

const MenuIcon = "ph:list-light"
const SplitIcon = "carbon:draggable"

const splitPane = ref()
const splitDefault = ref(0.3)
const splitDisabled = ref(false)

const slots = useSlots()
const sidebarOpen = ref(false)
const sidebar = ref(null)
const mainScrollbar = ref<typeof NScrollbar | null>(null)
const sidebarAvailable = computed(
	() => !!slots["sidebar-header"] || !!slots["sidebar-content"] || !!slots["sidebar-footer"]
)

onClickOutside(sidebar, () => closeSidebar())

function closeSidebar() {
	sidebarOpen.value = false
}

function openSidebar() {
	sidebarOpen.value = true
}

watch(
	sidebarOpen,
	val => {
		emit("sidebar", val)
	},
	{ immediate: true }
)

const { width } = useWindowSize()

watch(
	width,
	val => {
		splitDefault.value = val <= 700 ? 0 : 0.3
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
	--mb-toolbar-height: 70px;
	position: relative;
	height: 100%;
	overflow: hidden;
	border-radius: var(--border-radius);
	border: 1px solid var(--border-color);
	background-color: var(--bg-color);
	direction: ltr;

	:deep() {
		.n-split-pane-1,
		.n-split-pane-2 {
			overflow: hidden;
			height: 100%;
		}
		.n-split-pane-1 {
			min-width: 250px;
			max-width: min(450px, calc(100% - 400px));
		}
	}

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
			background-color: var(--primary-010-color);

			.split-trigger-icon {
				background-color: var(--primary-010-color);
			}
		}
	}

	.sidebar {
		background-color: var(--bg-secondary-color);
		min-width: 250px;
		//max-width: calc(100% - 400px);
		//width: 35%;
		height: 100%;
		overflow: hidden;
		border-right: 1px solid var(--border-color);

		.sidebar-header {
			border-block-end: var(--border-small-050);
			min-height: var(--mb-toolbar-height);
			height: var(--mb-toolbar-height);
			padding: 0 30px;
		}

		.sidebar-main {
			overflow: hidden;

			.sidebar-main-content {
				padding: 30px;
			}
		}

		.sidebar-footer {
			border-block-start: var(--border-small-050);
			min-height: var(--mb-toolbar-height);
			padding: 0 30px;
		}
	}

	.main {
		background-color: var(--bg-color);
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
			border-block-end: var(--border-small-050);
			min-height: var(--mb-toolbar-height);
			height: var(--mb-toolbar-height);
			padding: 0 30px;
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
				padding: 30px;
			}
		}

		.main-footer {
			container-type: inline-size;
			border-block-start: var(--border-small-050);
			padding: 0 30px;

			.wrap {
				min-height: calc(var(--mb-toolbar-height) - 1px);
				width: 100%;
				display: flex;
				align-items: center;
			}
		}
	}

	&.sidebar-position-right {
		flex-direction: row-reverse;

		.sidebar {
			border-right: none;
			border-left: 1px solid var(--border-color);
		}
	}

	@media (max-width: 700px) {
		--mb-toolbar-height: 62px;
		height: 100%;
		overflow: hidden;
		border-radius: 0;
		border: none;

		:deep() {
			.n-split-pane-1 {
				min-width: 0;
				max-width: 0;
			}
		}

		&::before {
			content: "";
			width: 100vw;
			display: block;
			background-color: var(--bg-body);
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
				background-color: var(--bg-color);
				z-index: -1;
				position: absolute;
			}

			.sidebar-header,
			.sidebar-footer {
				padding: 0 20px;
			}

			.sidebar-main {
				.sidebar-main-content {
					padding: 20px;
				}
			}
		}
		.main {
			.main-toolbar {
				padding: 0 20px;
				gap: 14px;

				.menu-btn {
					display: flex;
				}
			}

			.main-view {
				.main-content {
					padding: 20px;
				}
			}
			.main-footer {
				padding: 0 20px;
			}
		}

		&.sidebar-position-right {
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
