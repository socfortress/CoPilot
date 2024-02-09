<template>
	<div class="wrapper flex grow" :class="[{ 'sidebar-open': sidebarOpen }, `sidebar-position-${sidebarPosition}`]">
		<div class="sidebar flex flex-col" ref="sidebar">
			<div class="sidebar-header flex items-center">
				<slot name="sidebar-header"></slot>
			</div>
			<div class="sidebar-main grow">
				<n-scrollbar style="max-height: 100%">
					<div class="sidebar-main-content">
						<slot name="sidebar-content"></slot>
					</div>
				</n-scrollbar>
			</div>
			<div class="sidebar-footer flex items-center">
				<slot name="sidebar-footer"></slot>
			</div>
		</div>

		<div class="main flex-grow flex flex-col">
			<div class="main-toolbar flex items-center">
				<div class="menu-btn flex justify-center opacity-50">
					<n-button text @click="sidebarOpen = true">
						<Icon :size="24" :name="MenuIcon"></Icon>
					</n-button>
				</div>

				<div>
					<slot name="main-toolbar"></slot>
				</div>
			</div>
			<div class="main-view grow">
				<n-scrollbar style="max-height: 100%">
					<div class="main-content">
						<slot name="main-content"></slot>
					</div>
				</n-scrollbar>
			</div>
			<div class="main-footer flex items-center">
				<slot name="main-footer"></slot>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { NScrollbar, NButton } from "naive-ui"
import Icon from "@/components/common/Icon.vue"

const MenuIcon = "ion:menu-sharp"
import { ref, toRefs } from "vue"
import { onClickOutside } from "@vueuse/core"

type SidebarPosition = "left" | "right"

const props = withDefaults(
	defineProps<{
		sidebarPosition?: SidebarPosition
	}>(),
	{ sidebarPosition: "left" }
)
const { sidebarPosition } = toRefs(props)

const sidebarOpen = ref(false)
const sidebar = ref(null)

onClickOutside(sidebar, () => (sidebarOpen.value = false))
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

	.sidebar {
		background-color: var(--bg-secondary-color);
		min-width: 250px;
		width: 40%;
		max-width: 350px;
		overflow: hidden;

		.sidebar-header {
			border-block-end: var(--border-small-050);
			min-height: var(--mb-toolbar-height);
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
		container-type: inline-size;

		.main-toolbar {
			border-block-end: var(--border-small-050);
			min-height: var(--mb-toolbar-height);
			padding: 0 30px;
			gap: 18px;
			line-height: 1.3;

			.menu-btn {
				display: none;
			}
		}

		.main-view {
			overflow: hidden;

			.main-content {
				padding: 30px;
			}
		}

		.main-footer {
			border-block-start: var(--border-small-050);
			min-height: var(--mb-toolbar-height);
			padding: 0 30px;
		}
	}

	&.sidebar-position-right {
		flex-direction: row-reverse;
	}

	@media (max-width: 700px) {
		--mb-toolbar-height: 62px;
		height: 100%;
		overflow: hidden;
		border-radius: 0;
		border: none;

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
			z-index: 1;

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
</style>
