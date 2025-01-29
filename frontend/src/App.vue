<template>
	<Provider>
		<component
			:is="layoutComponent"
			id="app-layout"
			:class="[
				`theme-${themeName}`,
				`layout-${layoutComponentName}`,
				`route-${routeName}`,
				{ 'opacity-0': loading }
			]"
		>
			<RouterView v-slot="{ Component: RouterComponent }">
				<transition :name="`router-${routerTransition}`" mode="out-in" appear>
					<component :is="RouterComponent" id="app-page" :key="routeName + forceRefresh" />
				</transition>
			</RouterView>
		</component>

		<SplashScreen :show="loading" />
		<SearchDialog v-if="isLogged" />
	</Provider>
</template>

<script lang="ts" setup>
import type { Layout, RouterTransition, ThemeNameEnum } from "@/types/theme.d"
import type { Component } from "vue"
import type { RouteLocationNormalized } from "vue-router"
import Blank from "@/app-layouts/Blank"
import Provider from "@/app-layouts/common/Provider.vue"
import SplashScreen from "@/app-layouts/common/SplashScreen.vue"
import HorizontalNav from "@/app-layouts/HorizontalNav"
import SearchDialog from "@/components/common/SearchDialog.vue"
import { useAuthStore } from "@/stores/auth"
import { useMainStore } from "@/stores/main"
import { useThemeStore } from "@/stores/theme"
import { computed, onBeforeMount, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import "@/assets/scss/index.scss"

const router = useRouter()
const route = useRoute()
const loading = ref(true)

const layoutComponents = {
	HorizontalNav,
	Blank
}

const themeStore = useThemeStore()
const mainStore = useMainStore()
const authStore = useAuthStore()

const routeName = computed<string>(() => route?.name?.toString() || "")
const forceRefresh = computed<number>(() => mainStore.forceRefresh)
const forceLayout = ref<Layout | null>(null)
const layout = computed<Layout>(() => themeStore.layout)
const layoutComponentName = computed<Layout>(() => forceLayout.value || layout.value)
const layoutComponent = computed<Component>(() => layoutComponents[layoutComponentName.value])
const routerTransition = computed<RouterTransition>(() => themeStore.routerTransition)
const themeName = computed<ThemeNameEnum>(() => themeStore.themeName)
const isLogged = computed(() => authStore.isLogged)

function checkThemeOverrides(currentRoute: RouteLocationNormalized) {
	if (currentRoute.meta?.theme?.layout !== undefined) {
		forceLayout.value = currentRoute.meta.theme.layout
	} else {
		forceLayout.value = null
	}
}

watch(layoutComponentName, () => {
	loading.value = false
})

router.afterEach(currentRoute => {
	checkThemeOverrides(currentRoute)
})

onBeforeMount(() => {
	checkThemeOverrides(route)

	setTimeout(() => {
		loading.value = false
	}, 500)
})
</script>
