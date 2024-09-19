<template>
	<div class="pinned-pages flex items-center gap-5 relative overflow-hidden py-2 justify-end w-full">
		<TransitionGroup name="anim" tag="div" class="flex items-center gap-4 overflow-hidden latest-list">
			<n-tag
				v-for="page of latestSanitized"
				:key="page.name"
				round
				:bordered="false"
				:closable="false"
				class="bg-transparent flex-shrink overflow-hidden p-0 transition-all duration-300"
				@close="removeLatestPage(page.name)"
			>
				<span
					:title="page.title"
					class="cursor-pointer ml-0.5 overflow-hidden text-ellipsis hover:underline hover:decoration-2 hover:decoration-[var(--primary-color)]"
					@click="gotoPage(page.name)"
				>
					{{ page.title }}
				</span>
				<template #icon>
					<div
						class="cursor-pointer transition-colors duration-300 mr-0.5 hover:text-[var(--primary-color)]"
						@click="pinPage(page)"
					>
						<Icon :size="14" :name="PinnedIcon"></Icon>
					</div>
				</template>
			</n-tag>
		</TransitionGroup>

		<Transition name="anim" tag="div" class="flex items-center shortcuts-container">
			<div v-if="pinned.length" class="flex items-center">
				<n-popover :show-arrow="false" placement="bottom-end" trigger="hover" class="!p-1">
					<template #trigger>
						<n-button size="small" class="!h-8">
							<span class="flex items-center gap-3">
								Shortcuts
								<n-badge :value="pinned.length" :color="style['divider-030-color']" />
							</span>
						</n-button>
					</template>
					<div class="flex flex-col">
						<n-button
							v-for="page of pinned"
							:key="page.name"
							size="small"
							quaternary
							class="!justify-start"
							@click="gotoPage(page.name)"
						>
							<template #icon>
								<Icon
									:size="20"
									:name="CloseIcon"
									class="opacity-50 hover:text-red-500 hover:opacity-100"
									@click.stop="removePinnedPage(page.name)"
								></Icon>
							</template>
							{{ page.title }}
						</n-button>
					</div>
				</n-popover>
			</div>
		</Transition>
	</div>
</template>

<script lang="ts" setup>
import Icon from "@/components/common/Icon.vue"
import { useThemeStore } from "@/stores/theme"
import { type RemovableRef, useStorage } from "@vueuse/core"
import _split from "lodash/split"
import _takeRight from "lodash/takeRight"
import _uniqBy from "lodash/uniqBy"
import { NBadge, NButton, NPopover, NTag } from "naive-ui"
import { computed, type ComputedRef } from "vue"
import { type RouteLocationNormalized, type RouteRecordName, useRouter } from "vue-router"

interface Page {
	name: RouteRecordName | string
	fullPath: string
	title: string
}

const PinnedIcon = "tabler:pinned"
const CloseIcon = "carbon:close"
const router = useRouter()
const themeStore = useThemeStore()
const style = computed(() => themeStore.style)
const latest: RemovableRef<Page[]> = useStorage<Page[]>("latest-pages", [], sessionStorage)
const pinned: RemovableRef<Page[]> = useStorage<Page[]>("pinned-pages", [], localStorage)

function removeLatestPage(pageName: RouteRecordName | string) {
	latest.value = latest.value.filter(page => page.name !== pageName)
	return true
}
function removePinnedPage(pageName: RouteRecordName | string) {
	pinned.value = pinned.value.filter(page => page.name !== pageName)
	return true
}
function gotoPage(pageName: RouteRecordName | string) {
	router.push({ name: pageName })
	return true
}

function pinPage(page: Page) {
	const isPresent = pinned.value.findIndex(p => p.name === page.name) !== -1
	if (!isPresent) {
		pinned.value = [page, ...pinned.value]
	}
	return true
}

const latestSanitized: ComputedRef<Page[]> = computed(() => {
	return _takeRight(
		latest.value.filter(page => pinned.value.findIndex(p => p.name === page.name) === -1).reverse(),
		3
	) as Page[]
})

function checkRoute(route: RouteLocationNormalized) {
	const title = route.meta?.title || _split(route.name?.toString(), "-").at(-1)

	if (route.name && title && !route.meta?.skipPin) {
		const page: Page = {
			name: route.name,
			fullPath: route.fullPath,
			title
		}
		latest.value = _uniqBy([page, ...latest.value, page], "name")
	}
}

router.afterEach(route => {
	checkRoute(route)
})
</script>

<style lang="scss" scoped>
.pinned-pages {
	container-type: inline-size;

	:deep() {
		.n-tag {
			background-color: transparent;
			flex-shrink: 1;
			overflow: hidden;

			&.n-tag--round {
				padding: 0;
				transition: all 0.3s;
			}
			.n-tag__icon {
				margin: 0 !important;
			}
			.n-tag__content {
				overflow: hidden;
				text-overflow: ellipsis;
			}
			.n-tag__close {
				overflow: hidden;
				width: 0px;
				margin-left: 0;
				margin-right: 0;
				transition: all 0.3s;
			}

			&.n-tag--closable {
				&:hover {
					background-color: var(--bg-sidebar);

					&.n-tag--round {
						padding: 0 calc(var(--n-height) / 3.6) 0 calc(var(--n-height) / 3.6);
					}
					.n-tag__close {
						margin-left: 5px;
						overflow: initial;
						width: 14px;
					}
				}
			}
		}
	}

	.anim-move,
	.anim-enter-active,
	.anim-leave-active {
		transition: all 0.5s var(--bezier-ease);
	}

	.anim-enter-from,
	.anim-leave-to {
		opacity: 0;
		transform: scale(0);
	}

	.anim-leave-active {
		position: absolute;
	}

	@container (max-width: 460px) {
		.latest-list {
			display: none;
		}
	}

	@container (max-width: 140px) {
		.shortcuts-container {
			display: none;
		}
	}
}
</style>
