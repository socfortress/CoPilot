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
import type { Component } from "vue"
import type { RouteLocationNormalized } from "vue-router"
import type { Layout, RouterTransition, ThemeNameEnum } from "@/types/theme"
import { computed, onBeforeMount, onMounted, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import Blank from "@/app-layouts/Blank"
import Provider from "@/app-layouts/common/Provider.vue"
import SplashScreen from "@/app-layouts/common/SplashScreen.vue"
import HorizontalNav from "@/app-layouts/HorizontalNav"
import SearchDialog from "@/components/common/SearchDialog.vue"
import { useAuthStore } from "@/stores/auth"
import { useMainStore } from "@/stores/main"
import { useThemeStore } from "@/stores/theme"
import { usePortalSettingsStore } from "./stores/portalSettings"

const layoutComponents = {
	HorizontalNav,
	Blank
}

const router = useRouter()
const route = useRoute()
const loading = ref(true)

const portalSettingsStore = usePortalSettingsStore()
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

// Function to convert logo to favicon format (32x32 PNG)
async function logoToFavicon(logoDataUri: string) {
	const img = await createImageBitmap(await (await fetch(logoDataUri)).blob())
	// Canvas a 32x32
	const canvas = new OffscreenCanvas(32, 32)
	const ctx = canvas.getContext("2d")
	if (!ctx) throw new Error("Failed to get canvas context")

	ctx.drawImage(img, 0, 0, 32, 32)
	const blob = await canvas.convertToBlob({ type: "image/png" })

	// Convert blob to data URL
	return new Promise<string>((resolve, reject) => {
		const reader = new FileReader()
		reader.onloadend = () => resolve(reader.result as string)
		reader.onerror = reject
		reader.readAsDataURL(blob)
	})
}

// Function to update favicon
async function updateFavicon(logoDataUrl: string | null) {
	if (!logoDataUrl) return

	try {
		// Convert logo to ICO format
		const faviconDataUrl = await logoToFavicon(logoDataUrl)

		// Remove existing favicon links
		const existingLinks = document.querySelectorAll("link[rel*='icon']")
		existingLinks.forEach(link => link.remove())

		// Create new favicon link
		const link = document.createElement("link")
		link.rel = "icon"
		link.type = "image/png"
		link.href = faviconDataUrl
		document.head.appendChild(link)
	} catch (error) {
		console.error("Failed to update favicon:", error)
	}
}

// Fetch portal settings on app mount
onMounted(async () => {
	await portalSettingsStore.fetchSettings()
})

// Watch for logo changes and update favicon
watch(
	() => portalSettingsStore.portalLogo,
	newLogo => {
		if (newLogo) {
			updateFavicon(newLogo)
		}
	},
	{ immediate: true }
)

// Watch for title changes and update document title
watch(
	() => portalSettingsStore.portalTitle,
	newTitle => {
		if (newTitle) {
			document.title = newTitle
		}
	},
	{ immediate: true }
)

watch(layoutComponentName, () => {
	loading.value = false
})

router.afterEach(currentRoute => {
	checkThemeOverrides(currentRoute)
})

onBeforeMount(() => {
	authStore.loadProfile()
	checkThemeOverrides(route)

	setTimeout(() => {
		loading.value = false
	}, 500)
})
</script>
