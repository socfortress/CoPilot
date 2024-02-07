<template>
	<n-breadcrumb class="breadcrumb">
		<n-breadcrumb-item @click="goto({ path: '/' })">
			<Icon :size="16" :name="HomeIcon"></Icon>
		</n-breadcrumb-item>
		<TransitionGroup name="anim">
			<n-breadcrumb-item
				v-for="(item, index) of items"
				:key="item.key"
				:clickable="false"
				:class="`index-${index}`"
			>
				{{ item.name }}
			</n-breadcrumb-item>
		</TransitionGroup>
	</n-breadcrumb>
</template>

<script lang="ts" setup>
import { NBreadcrumb, NBreadcrumbItem } from "naive-ui"
import _upperCase from "lodash/upperCase"
import _capitalize from "lodash/capitalize"
import _split from "lodash/split"
import { type RouteLocationNormalizedLoaded } from "vue-router"
import { onBeforeMount, ref } from "vue"
import { useRouter, useRoute } from "vue-router"
import Icon from "@/components/common/Icon.vue"

const HomeIcon = "fluent:home-24-regular"

interface Page {
	name: string
	path: string
	key: string
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

function checkRoute(route: RouteLocationNormalizedLoaded) {
	const newItems: Page[] = []
	const pathChunks = route?.path?.indexOf("/") !== -1 ? _split(route?.path || "", "/") : [route?.path]

	for (const chunk of pathChunks) {
		if (chunk) {
			newItems.push({
				name: _capitalize(_upperCase(chunk)),
				path: chunk.toLowerCase(),
				key: chunk + new Date().getTime()
			})
		}
	}

	items.value = newItems
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
