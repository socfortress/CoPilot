<template>
	<n-alert v-if="showBanner" title="New version available!" type="info" closable @close="dismissBanner">
		<template #icon>
			<Icon :name="UpdateIcon" :size="18" />
		</template>
		<template #header>New version available!</template>
		<div v-if="versionInfo" class="flex flex-col">
			<div class="flex items-center justify-between gap-4">
				<div class="text-sm">
					You're running v{{ versionInfo.current_version }}, v{{ versionInfo.latest_version }} is now
					available.
					<span v-if="versionInfo.published_at" class="opacity-75">
						(Released {{ formatDate(versionInfo.published_at, dFormats.datetime) }})
					</span>
				</div>
				<div class="flex gap-2">
					<n-button v-if="showReleaseNotes" size="small" secondary @click="toggleNotes">
						{{ expandedNotes ? "Hide" : "Show" }} Release Notes
					</n-button>
					<n-button
						v-if="versionInfo.release_url"
						tag="a"
						:href="versionInfo.release_url"
						target="_blank"
						size="small"
						type="primary"
					>
						View on GitHub
					</n-button>
				</div>
			</div>
			<n-collapse-transition :show="expandedNotes">
				<n-card v-if="versionInfo.release_notes" class="mt-4" content-class="pr-2!">
					<n-scrollbar class="max-h-50 pr-4">
						<Markdown :source="versionInfo.release_notes" breaks />
					</n-scrollbar>
				</n-card>
			</n-collapse-transition>
		</div>
	</n-alert>
</template>

<script setup lang="ts">
import type { VersionCheckResponse } from "@/types/version.d"
import { useStorage } from "@vueuse/core"
import { NAlert, NButton, NCard, NCollapseTransition, NScrollbar } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import Markdown from "@/components/common/Markdown.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"

const UpdateIcon = "carbon:update-now"
const versionInfo = ref<VersionCheckResponse | null>(null)
const showBanner = ref(false)
const expandedNotes = ref(false)

const dFormats = useSettingsStore().dateFormat
const DISMISS_KEY = "version_banner_dismissed"
const DISMISS_DURATION = 24 * 60 * 60 * 1000 // 24 hours

const dismissedAt = useStorage<number | null>(DISMISS_KEY, null)

const showReleaseNotes = computed(() => {
	return versionInfo.value?.release_notes && versionInfo.value.release_notes.trim().length > 0
})

function toggleNotes() {
	expandedNotes.value = !expandedNotes.value
}

function checkIfDismissed() {
	if (dismissedAt.value) {
		// Show again after 24 hours
		return Date.now() - dismissedAt.value < DISMISS_DURATION
	}
	return false
}

function dismissBanner() {
	dismissedAt.value = Date.now()
	showBanner.value = false
}

async function checkVersion() {
	// Don't check if recently dismissed
	if (checkIfDismissed()) {
		return
	}

	try {
		const response = await Api.version.checkVersion()
		if (response.data.success) {
			versionInfo.value = response.data
			showBanner.value = response.data.is_outdated
		}
	} catch (err) {
		// Silently fail - version check is not critical
		console.warn("Failed to check version:", err)
	}
}

onBeforeMount(() => {
	checkVersion()
})
</script>
