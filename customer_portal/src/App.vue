<template>
	<router-view />
</template>

<script setup lang="ts">
import { onMounted, watch } from "vue"
import { usePortalSettingsStore } from "./stores/portalSettings"

const portalSettingsStore = usePortalSettingsStore()

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
const updateFavicon = async (logoDataUrl: string | null) => {
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
</script>

<style scoped>
/* Any app-level styles can go here */
</style>
