<template>
	<div class="flex pinned-pages items-end">
		<XyzTransitionGroup class="latest-list flex items-center" xyz="fade stagger-1 down-1">
			<n-tag
				round
				:bordered="false"
				closable
				v-for="page of latestSanitized"
				:key="page.name"
				@close="removeLatestPage(page.name)"
			>
				<span class="page-name" @click="gotoPage(page.name)">
					{{ page.title }}
				</span>
				<template #icon>
					<div class="icon-box" @click="pinPage(page)">
						<n-icon :component="page.icon" :size="14" class="no-hover" />
						<n-icon :component="PinnedIcon" :size="14" class="hover" />
					</div>
				</template>
			</n-tag>
		</XyzTransitionGroup>

		<div class="divider" v-if="latestSanitized.length && pinned.length"></div>
		<XyzTransitionGroup class="pinned-list flex items-center" xyz="fade stagger-1 down-1">
			<n-tag
				round
				:bordered="false"
				closable
				v-for="page of pinned"
				:key="page.name"
				@close="removePinnedPage(page.name)"
			>
				<template #icon>
					<n-tooltip trigger="hover">
						<template #trigger>
							<div class="icon-box" @click="gotoPage(page.name)">
								<n-icon :component="page.icon" :size="18" />
							</div>
						</template>
						{{ page.title }}
					</n-tooltip>
				</template>
			</n-tag>
		</XyzTransitionGroup>
		<div class="bar"></div>
	</div>
</template>

<script lang="ts" setup>
import { useRouter, type RouteRecordName } from "vue-router"
import { type RemovableRef, useStorage, type Serializer } from "@vueuse/core"
import { computed, type ComputedRef, type DefineComponent } from "vue"
import _uniqBy from "lodash/uniqBy"
import PinnedIcon from "@vicons/tabler/Pinned"
import { NIcon, NTag, NTooltip } from "naive-ui"
import _takeRight from "lodash/takeRight"

interface Page {
	name: RouteRecordName | string
	fullPath: string
	title: string
	icon: DefineComponent
}

defineOptions({
	name: "PinnedPages"
})

const router = useRouter()

const serializer: Serializer<Page[]> = {
	read: (v: any) => {
		const list = JSON.parse(v)
		const tmp = []
		for (const item of list) {
			tmp.push({
				name: item.name,
				fullPath: item.fullPath,
				title: item.title,
				iconRender: item.iconRender,
				icon: {
					name: item.icon?.name,
					render() {
						return JSON.parse(item.iconRender)
					}
				} as unknown as DefineComponent
			})
		}
		return tmp || []
	},
	write: (v: any) => {
		const tmp = []
		for (const item of v) {
			tmp.push({
				name: item.name,
				fullPath: item.fullPath,
				title: item.title,
				icon: {
					name: item.icon?.name
				},
				iconRender: JSON.stringify(item.icon?.render() || {})
			})
		}
		return JSON.stringify(tmp)
	}
}

const removeLatestPage = (pageName: RouteRecordName | string) => {
	latest.value = latest.value.filter(page => page.name !== pageName)
	return true
}
const removePinnedPage = (pageName: RouteRecordName | string) => {
	pinned.value = pinned.value.filter(page => page.name !== pageName)
	return true
}
const gotoPage = (pageName: RouteRecordName | string) => {
	router.push({ name: pageName })
	return true
}
const pinPage = (page: Page) => {
	const isPresent = pinned.value.findIndex(p => p.name === page.name) !== -1
	if (!isPresent) {
		pinned.value = _uniqBy([page, ...pinned.value], "name").reverse()
	}
	return true
}
const latest: RemovableRef<Page[]> = useStorage<Page[]>("latest-pages", [], sessionStorage, {
	serializer,
	shallow: true
})
const pinned: RemovableRef<Page[]> = useStorage<Page[]>("pinned-pages", [], localStorage, {
	serializer,
	shallow: true
})

router.afterEach(route => {
	if (route.name && route.meta?.title) {
		const page: Page = {
			name: route.name,
			fullPath: route.fullPath,
			title: route.meta.title as string,
			icon: (route.meta?.icon || PinnedIcon) as DefineComponent
		}
		latest.value = _uniqBy([page, ...latest.value, page], "name")
	}
})

const latestSanitized: ComputedRef<Page[]> = computed(() => {
	return _takeRight(
		latest.value.filter(page => pinned.value.findIndex(p => p.name === page.name) === -1).reverse(),
		3
	) as Page[]
})
</script>

<style lang="scss" scoped>
.pinned-pages {
	position: relative;

	:deep() {
		.n-tag {
			&.n-tag--icon.n-tag--round {
				padding: 0 calc(var(--n-height) / 4.8) 0 calc(var(--n-height) / 4.8);
				transition: all 0.3s;
			}
			.n-tag__icon {
				margin: 0 !important;
			}
			.n-tag__close {
				overflow: hidden;
				width: 0px;
				margin-left: 0;
				margin-right: 0;
				transition: all 0.3s;
			}

			&:hover {
				&.n-tag--icon.n-tag--round {
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

	.pinned-list {
		--xyz-out-duration: 0;
		--xyz-out-delay: 0;

		:deep() {
			.n-tag {
				background-color: transparent;
				display: flex;
				flex-direction: row-reverse;

				.icon-box {
					padding: 0px;
					transition:
						padding 0.3s,
						width 0.3s;
				}

				&:hover {
					background-color: var(--bg-sidebar);

					.n-tag__close {
						margin-left: 0px;
						margin-right: 5px;
					}

					.icon-box {
						padding: 0 5px;
						width: 30px;
					}
				}
			}
		}
	}

	.latest-list {
		--xyz-out-duration: 0;
		--xyz-out-delay: 0;

		:deep() {
			.n-tag {
				background-color: transparent;

				&:hover {
					background-color: var(--bg-sidebar);
					.no-hover {
						opacity: 0;
					}
					.hover {
						opacity: 1;
					}
				}
			}
		}
	}

	.bar {
		background-color: var(--bg-sidebar);
		position: absolute;
		bottom: -7px;
		border-radius: 6px;
		left: 0;
		width: 100%;
		height: 4px;
	}

	.divider {
		height: 8px;
		width: 8px;
		position: relative;
		top: 9px;
		z-index: 1;
		border-radius: 50%;
		border: 2px solid var(--bg-body);
		opacity: 0.9;
		background-color: var(--primary-color);
	}

	.page-name {
		cursor: pointer;
		margin-left: 3px;
		margin-right: 4px;

		&:hover {
			text-decoration: underline;
			text-decoration-thickness: 2px;
			text-decoration-color: var(--primary-color);
		}
	}
	.icon-box {
		cursor: pointer;
		width: 20px;
		height: 20px;
		position: relative;
		display: flex;
		justify-content: center;
		align-items: center;
		transition: color 0.3s;

		:deep() {
			.n-icon {
				position: absolute;
			}
		}

		.no-hover {
			opacity: 1;
			transition: opacity 0.3s;
		}
		.hover {
			opacity: 0;
			transition: opacity 0.3s;
		}

		&:hover {
			color: var(--primary-color);

			.no-hover {
				opacity: 0;
			}
			.hover {
				opacity: 1;
			}
		}
	}
}
</style>
