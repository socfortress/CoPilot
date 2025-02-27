<template>
	<n-breadcrumb class="breadcrumb">
		<n-breadcrumb-item @click="goto({ path: '/' })">
			<Icon :size="16" :name="HomeIcon" />
		</n-breadcrumb-item>
		<TransitionGroup name="anim">
			<n-breadcrumb-item
				v-for="(item, index) of items"
				:key="item.key"
				:class="`index-${index}`"
				@click="goto({ path: item.path })"
			>
				{{ item.name }}
			</n-breadcrumb-item>
		</TransitionGroup>
	</n-breadcrumb>
</template>

<script lang="ts" setup>
import type { RouteLocationNormalizedLoaded } from "vue-router"
import Icon from "@/components/common/Icon.vue"
import _capitalize from "lodash/capitalize"
import _compact from "lodash/compact"
import _isEqual from "lodash/isEqual"
import _split from "lodash/split"
import { NBreadcrumb, NBreadcrumbItem } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import { useRoute, useRouter } from "vue-router"

interface Page {
	name: string
	path: string
	key: string
}

const HomeIcon = "fluent:home-24-regular"
const router = useRouter()
const route = useRoute()
const items = ref<Page[]>([])

function goto(page: Partial<Page>) {
	if (page.name && page.name !== route.name) {
		router.push({ name: page.name })
	}
	if (page.path && page.path !== route.path) {
		router.push({ path: page.path })
	}
}

function checkRoute(route: RouteLocationNormalizedLoaded) {
	const newItems: Page[] = []
	let pathChunks = _compact(_split(route?.path || "", "/"))
	if (!pathChunks.length) {
		pathChunks = _compact(_split(route?.matched?.[0]?.aliasOf?.path || "", "/"))
	}

	let cumulativePath = ""

	for (const chunk of pathChunks) {
		const name = _capitalize(chunk)
		cumulativePath += `/${chunk}`

		newItems.push({
			name,
			path: cumulativePath,
			key: name + cumulativePath
		})
	}

	if (route.meta?.title && newItems.length) {
		newItems[newItems.length - 1].name = route.meta.title
	}

	if (!_isEqual(items.value, newItems)) {
		items.value = newItems
	}
}

onBeforeMount(() => {
	checkRoute(router.currentRoute.value)

	router.beforeResolve(route => {
		checkRoute(route)
	})
})
</script>

<style lang="scss" scoped>
.breadcrumb {
	.anim-move,
	.anim-enter-active {
		transition: all 0.5s var(--bezier-ease);

		@for $i from 0 through 10 {
			&.index-#{$i} {
				transition-delay: $i * 0.1s;
			}
		}
	}

	.anim-leave-active {
		display: none;
	}

	.anim-enter-from {
		opacity: 0;
		transform: translateX(-5px);
	}
}
</style>
