<template>
	<n-breadcrumb class="breadcrumb">
		<XyzTransitionGroup class="item-group" xyz="fade stagger-1 left-1">
			<n-breadcrumb-item @click="goto({ path: '/' })" :key="'///'">
				<n-icon :size="16"><Home24Regular /></n-icon>
			</n-breadcrumb-item>
			<n-breadcrumb-item
				v-for="item of items"
				:key="item.key"
				@click="item.children?.length ? () => {} : goto(item)"
			>
				<n-dropdown :options="item.children" v-if="item.children?.length">
					<div class="trigger">
						{{ item.title }}
					</div>
				</n-dropdown>
				<span v-else>
					{{ item.title }}
				</span>
			</n-breadcrumb-item>
		</XyzTransitionGroup>
	</n-breadcrumb>
</template>

<script lang="ts" setup>
import { NBreadcrumb, NBreadcrumbItem, NIcon, NDropdown } from "naive-ui"
import Home24Regular from "@vicons/fluent/Home24Regular"
import _trim from "lodash/trim"
import _capitalize from "lodash/capitalize"
import { type RouteLocationNormalizedLoaded, type RouteRecordNormalized, type RouteRecordRaw } from "vue-router"
import { onBeforeMount, ref } from "vue"
import { useRouter, useRoute } from "vue-router"

interface Page {
	name: string
	path: string
	title: string
	children?: Page[]
	props?: { onClick: () => void }
	label?: string
	key?: string
}

defineOptions({
	name: "Breadcrumb"
})

const router = useRouter()
const route = useRoute()

const items = ref<Page[]>([])

function goto(page: Partial<Page>) {
	if (page.name && page.name !== route.name) {
		router.push({ name: page.name })
		return
	}
	if (page.path && page.path !== route.path) {
		router.push({ path: page.path })
		return
	}
}
function transformRoute(route: RouteRecordNormalized | RouteRecordRaw): Page {
	const name = route.name?.toString() || ""
	const path = route.path?.toString() || ""
	const title = route.meta?.title?.toString() || _capitalize(name || _trim(path, "/"))
	const label = title
	const key = name || path
	const props = {
		onClick: () => {
			goto({ name, path })
		}
	}

	return { name, path, title, props, label, key }
}
function checkRoute(route: RouteLocationNormalizedLoaded) {
	const newItems: Page[] = []

	if (route?.matched?.length) {
		for (const match of route.matched) {
			const partial = transformRoute(match)
			if (match.children?.length) {
				partial.children =
					match.children
						.filter(p => p.name !== route.name && p.path !== route.path)
						.map(p => transformRoute(p)) || []
			}

			if (partial.name || partial.path) {
				newItems.push(partial)
			}
		}
	}

	items.value = newItems
}

onBeforeMount(() => {
	checkRoute(router.currentRoute.value)

	router.afterEach(route => {
		checkRoute(route)
	})
})
</script>

<style lang="scss" scoped>
.item-group {
	--xyz-out-duration: 0;
	--xyz-out-delay: 0;
}
</style>
