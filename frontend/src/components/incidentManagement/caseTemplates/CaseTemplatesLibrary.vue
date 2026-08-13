<template>
	<div class="@container flex flex-col gap-4">
		<!-- Header / actions -->
		<div class="flex flex-col gap-2">
			<div class="flex flex-wrap items-center justify-between gap-3">
				<div class="flex items-center gap-3">
					<h2>Template Library</h2>
					<a
						:href="REPO_URL"
						target="_blank"
						rel="noopener"
						class="text-secondary text-sm"
						title="Source repository on GitHub"
					>
						{{ REPO_NAME }} ↗
					</a>
				</div>
				<div class="flex items-center gap-2">
					<div v-if="lastRefresh" class="text-tertiary text-xs">
						Cached
						{{ formatDate(lastRefresh, dFormats.datetimesec, { tz: true }) }}
					</div>
					<n-button size="small" secondary :loading="refreshing" @click="refresh">
						<template #icon><Icon name="carbon:renew" /></template>
						Refresh
					</n-button>
				</div>
			</div>

			<p class="text-secondary text-sm">
				Read-only catalog of investigation playbooks. Click
				<strong>Import</strong>
				to materialise a playbook as a normal case template you can apply to cases. Edits made in CoPilot after
				import don't flow back to the source repo, and changes pushed to the repo don't retroactively update
				already-imported templates.
			</p>

			<n-alert v-if="invalidPaths.length" type="warning" :show-icon="false">
				<template #header>{{ invalidPaths.length }} library file(s) failed validation</template>
				<div class="flex flex-wrap gap-2 text-xs">
					<code v-for="p of invalidPaths" :key="p">{{ p }}</code>
				</div>
			</n-alert>
		</div>

		<!-- Filter -->
		<div class="mt-2">
			<n-input
				v-model:value="search"
				size="small"
				placeholder="Search by name, description, or source"
				clearable
				class="max-w-96"
			>
				<template #prefix><Icon name="carbon:search" /></template>
			</n-input>
		</div>

		<n-spin :show="loading" class="min-h-48">
			<div v-if="filteredEntries.length" class="grid grid-cols-1 gap-3 @3xl:grid-cols-2 @6xl:grid-cols-3">
				<CaseTemplateLibraryItem
					v-for="entry of filteredEntries"
					:key="entry.key"
					:entry
					:importing="importingKey === entry.key"
					:import-disabled="importingKey !== null"
					@import="openImport($event)"
				/>
			</div>

			<n-empty
				v-else-if="!loading && entries.length === 0"
				description="No library entries found. The repo may be empty or unreachable."
				class="h-40 justify-center"
			>
				<template #extra>
					<n-button size="small" @click="refresh">Retry</n-button>
				</template>
			</n-empty>

			<n-empty v-else-if="!loading" description="No entries match your search." class="h-32 justify-center" />
		</n-spin>

		<CaseTemplateLibraryImportModal v-model:show="showImport" :entry="selectedEntry" @imported="onImported" />
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { CaseTemplateLibraryEntry } from "@/types/incidentManagement/case-templates"
import { NAlert, NButton, NEmpty, NInput, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import CaseTemplateLibraryImportModal from "./CaseTemplateLibraryImportModal.vue"
import CaseTemplateLibraryItem from "./CaseTemplateLibraryItem.vue"

const emit = defineEmits<{
	(e: "imported"): void
}>()

const REPO_NAME = "socfortress/CoPilot-Case-Templates"
const REPO_URL = `https://github.com/${REPO_NAME}`

const message = useMessage()
const dFormats = useSettingsStore().dateFormat

const entries = ref<CaseTemplateLibraryEntry[]>([])
const invalidPaths = ref<string[]>([])
const lastRefresh = ref<string | null>(null)
const loading = ref(false)
const refreshing = ref(false)
const importingKey = ref<string | null>(null)
const search = ref<string | null>(null)

const showImport = ref(false)
const selectedEntry = ref<CaseTemplateLibraryEntry | null>(null)

const filteredEntries = computed(() => {
	const q = (search.value || "").trim().toLowerCase()

	if (!q) return entries.value

	return entries.value.filter(e => {
		const haystack = `${e.name} ${e.description ?? ""} ${e.source ?? ""}`.toLowerCase()
		return haystack.includes(q)
	})
})

function load() {
	loading.value = true

	Api.incidentManagement.caseTemplates
		.getLibrary()
		.then(res => {
			entries.value = res.data.entries || []
			invalidPaths.value = res.data.invalid_paths || []
			lastRefresh.value = res.data.last_refresh || null

			if (!res.data.success) {
				message.warning(res.data.message || "Failed to load case-template library")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "Failed to load case-template library")
		})
		.finally(() => {
			loading.value = false
		})
}

async function refresh() {
	refreshing.value = true

	try {
		const res = await Api.incidentManagement.caseTemplates.refreshLibrary()
		if (res.data.success) {
			message.success(res.data.message)
		} else {
			message.warning(res.data.message)
		}
		load()
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Failed to refresh case-template library")
	} finally {
		refreshing.value = false
	}
}

function openImport(entry: CaseTemplateLibraryEntry) {
	selectedEntry.value = entry
	showImport.value = true
}

function onImported() {
	// Bubble up so the parent (CaseTemplatesList) can refresh its own list
	// and switch the user back to the Templates tab.
	emit("imported")
}

onBeforeMount(load)
</script>
