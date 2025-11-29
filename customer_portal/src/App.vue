<template>
	<router-view />
</template>

<script setup lang="ts">
import { onMounted, watch } from "vue"
import { usePortalSettingsStore } from "./stores/portalSettings"

const portalSettingsStore = usePortalSettingsStore()

// Function to update favicon
const updateFavicon = (logoDataUrl: string | null) => {
	if (!logoDataUrl) return

	// Remove existing favicon links
	const existingLinks = document.querySelectorAll("link[rel*='icon']")
	existingLinks.forEach(link => link.remove())

	// Create new favicon link
	const link = document.createElement("link")
	link.rel = "icon"
	link.type = "image/x-icon"
	link.href = logoDataUrl
	document.head.appendChild(link)
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
</script>

<style scoped>
/* Any app-level styles can go here */
</style>
