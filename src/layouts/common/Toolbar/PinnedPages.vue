<template>
	<div class="flex pinned-pages items-end">
		<TransitionGroup name="anim" tag="div" class="latest-list flex items-center gap-4">
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
						<Icon :size="14" :name="PinnedIcon"></Icon>
					</div>
				</template>
			</n-tag>
		</TransitionGroup>

		<div class="divider" v-if="latestSanitized.length && pinned.length"></div>

		<TransitionGroup name="anim" tag="div" class="pinned-list flex items-center gap-4">
			<n-tag
				round
				:bordered="false"
				closable
				v-for="page of pinned"
				:key="page.name"
				@close="removePinnedPage(page.name)"
			>
				<div class="page-name" @click="gotoPage(page.name)">
					{{ page.title }}
				</div>
			</n-tag>
		</TransitionGroup>
		<div class="bar"></div>
	</div>
</template>

<script lang="ts" setup>
import { useRouter, type RouteRecordName } from "vue-router"
import { type RemovableRef, useStorage } from "@vueuse/core"
import { computed, type ComputedRef } from "vue"
import { NTag } from "naive-ui"
import _takeRight from "lodash/takeRight"
import _split from "lodash/split"
import _uniqBy from "lodash/uniqBy"
import Icon from "@/components/common/Icon.vue"

const PinnedIcon = "tabler:pinned"

interface Page {
	name: RouteRecordName | string
	fullPath: string
	title: string
}

defineOptions({
	name: "PinnedPages"
})

const router = useRouter()

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
		pinned.value = [page, ...pinned.value]
	}
	return true
}
const latest: RemovableRef<Page[]> = useStorage<Page[]>("latest-pages", [], sessionStorage)
const pinned: RemovableRef<Page[]> = useStorage<Page[]>("pinned-pages", [], localStorage)

const latestSanitized: ComputedRef<Page[]> = computed(() => {
	return _takeRight(
		latest.value.filter(page => pinned.value.findIndex(p => p.name === page.name) === -1).reverse(),
		3
	) as Page[]
})

router.afterEach(route => {
	const title = route.meta?.title || _split(route.name?.toString(), "-").at(-1)

	if (route.name && title) {
		const page: Page = {
			name: route.name,
			fullPath: route.fullPath,
			title
		}
		latest.value = _uniqBy([page, ...latest.value, page], "name")
	}
})
</script>

<style lang="scss" scoped>
.pinned-pages {
	position: relative;

	:deep() {
		.n-tag {
			background-color: transparent;

			&.n-tag--round {
				padding: 0;
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

	.pinned-list {
		.page-name {
			color: var(--primary-color);
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
		margin: 0 8px;
	}

	.page-name {
		cursor: pointer;
		margin-left: 2px;

		&:hover {
			text-decoration: underline;
			text-decoration-thickness: 2px;
			text-decoration-color: var(--primary-color);
		}
	}
	.icon-box {
		cursor: pointer;
		transition: color 0.3s;
		margin-right: 2px;

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
}
</style>
