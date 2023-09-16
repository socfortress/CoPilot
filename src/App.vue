<template>
	<Provider>
		<component :is="layoutComponent" :class="[`theme-${themeName}`, `layout-${layout}`, themeName]">
			<RouterView v-slot="{ Component }">
				<transition :name="`router-${routerTransition}`" mode="out-in" appear>
					<component
						:is="Component"
						:key="forceRefresh"
						:class="[`theme-${themeName}`, `layout-${layout}`, themeName]"
					/>
				</transition>
			</RouterView>
		</component>

		<SplashScreen :loading="loading" />
		<LayoutSettings />
	</Provider>
</template>

<script lang="ts" setup>
import { useMainStore } from "@/stores/main"
import VerticalNav from "@/layouts/VerticalNav"
import HorizontalNav from "@/layouts/HorizontalNav"
import Blank from "@/layouts/Blank"
import Provider from "@/layouts/common/Provider.vue"
import SplashScreen from "@/layouts/common/SplashScreen.vue"
import LayoutSettings from "@/components/LayoutSettings"
import { useThemeStore } from "@/stores/theme"
import { Layout, RouterTransition, type ThemeName } from "@/types/theme.d"
import { computed, onBeforeMount, ref } from "vue"
import type { Component } from "vue"
import { useRouter } from "vue-router"
import { authCheck } from "@/middleware/auth.global"

import "@/assets/scss/index.scss"

defineOptions({
	name: "App"
})

const router = useRouter()
const loading = ref(true)

const layoutComponents = {
	VerticalNav,
	HorizontalNav,
	Blank
}

const forceLayout = ref<Layout | null>(null)
const forceRefresh = computed<number>(() => useMainStore().forceRefresh)
const layout = computed<Layout>(() => useThemeStore().layout)
const layoutComponent = computed<Component>(() => layoutComponents[forceLayout.value || layout.value])
const routerTransition = computed<RouterTransition>(() => useThemeStore().routerTransition)
const themeName = computed<ThemeName>(() => useThemeStore().themeName)

router.beforeEach(route => {
	if (route.meta?.forceLayout) {
		forceLayout.value = route.meta.forceLayout
	} else {
		forceLayout.value = null
	}

	return authCheck(route)
})

onBeforeMount(() => {
	setTimeout(() => {
		loading.value = false
	}, 500)
})
</script>
