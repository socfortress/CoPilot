<template>
	<div class="pinned-pages flex items-center gap-5">
		<TransitionGroup name="anim" tag="div" class="latest-list flex items-center gap-4 overflow-hidden">
			<n-tag
				v-for="page of latestSanitized"
				:key="page.name"
				round
				:bordered="false"
				:closable="false"
				@close="removeLatestPage(page.name)"
			>
				<span class="page-name" :title="page.title" @click="gotoPage(page.name)">
					{{ page.title }}
				</span>
				<template #icon>
					<div class="icon-box" @click="pinPage(page)">
						<Icon :size="14" :name="PinnedIcon" />
					</div>
				</template>
			</n-tag>
		</TransitionGroup>

		<Transition name="anim" tag="div" class="shortcuts-container flex items-center">
			<div v-if="pinned.length" class="flex items-center">
				<n-popover :show-arrow="false" placement="bottom" trigger="hover" class="!p-1">
					<template #trigger>
						<button class="shortcuts-btn flex items-center gap-2">
							<span>Shortcuts</span>
							<n-badge :value="pinned.length" :color="style['divider-030-color']" />
						</button>
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
							<span class="flex items-center gap-1">
								<Icon
									:size="20"
									:name="CloseIcon"
									class="opacity-50 hover:text-red-500 hover:opacity-100"
									@click.stop="removePinnedPage(page.name)"
								/>
								<span class="px-2">
									{{ page.title }}
								</span>
							</span>
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
const latestSanitized: ComputedRef<Page[]> = computed(() => {
	return _takeRight(
		latest.value.filter(page => pinned.value.findIndex(p => p.name === page.name) === -1).reverse(),
		3
	) as Page[]
})

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
	position: relative;
	overflow: hidden;
	padding: 8px 0;
	container-type: inline-size;
	justify-content: flex-end;
	width: 100%;

	:deep() {
		.n-tag {
			background-color: transparent;
			flex-shrink: 1;
			overflow: hidden;
			gap: 4px;

			&.n-tag--round {
				padding: 0 !important;
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
					background-color: var(--hover-color);

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

	.shortcuts-btn {
		border-radius: 50px;
		background-color: var(--bg-color);
		gap: 10px;
		height: 32px;
		cursor: pointer;
		padding: 0px 8px;
		padding-left: 10px;
		outline: none;
		transition: all 0.2s var(--bezier-ease);
		border: none;

		&:hover {
			background-color: var(--hover-color);
		}
	}

	.page-name {
		cursor: pointer;
		overflow: hidden;
		text-overflow: ellipsis;

		&:hover {
			text-decoration: underline;
			text-decoration-thickness: 2px;
			text-decoration-color: var(--primary-color);
		}
	}

	.icon-box {
		cursor: pointer;
		transition: color 0.3s;

		&:hover {
			color: var(--primary-color);
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

.direction-rtl {
	.pinned-pages {
		.shortcuts-btn {
			padding-right: 10px;
			padding-left: 8px;
		}
	}
}
</style>
