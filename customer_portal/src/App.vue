<template>
	<router-view />
</template>

<script setup lang="ts">
import { onMounted } from "vue"
import { usePortalSettingsStore } from "./stores/portalSettings"

const portalSettingsStore = usePortalSettingsStore()

// Fetch portal settings on app mount
onMounted(async () => {
	await portalSettingsStore.fetchSettings()
})
</script>

<style scoped>
/* Any app-level styles can go here */
</style>
