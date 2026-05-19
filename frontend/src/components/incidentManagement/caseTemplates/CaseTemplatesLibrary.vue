<template>
	<div class="case-templates-library flex flex-col gap-4">
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

		<n-spin :show="loading">
			<div v-if="filteredEntries.length" class="grid grid-cols-1 gap-3 @2xl:grid-cols-2 @5xl:grid-cols-3">
				<div v-for="entry of filteredEntries" :key="entry.key" class="library-card">
					<div class="library-card-header flex items-start justify-between gap-2">
						<div class="flex min-w-0 flex-col">
							<div class="library-card-name truncate">{{ entry.name }}</div>
							<code v-if="entry.source" class="text-tertiary text-xs">{{ entry.source }}</code>
						</div>
						<n-button
							size="small"
							type="primary"
							secondary
							:disabled="importingKey !== null"
							:loading="importingKey === entry.key"
							@click="openImport(entry)"
						>
							<template #icon><Icon name="carbon:download" /></template>
							Import
						</n-button>
					</div>

					<p v-if="entry.description" class="text-secondary line-clamp-3 text-sm">
						{{ entry.description }}
					</p>

					<div class="library-card-meta flex flex-wrap items-center gap-2 text-xs">
						<Badge type="splitted">
							<template #label>Tasks</template>
							<template #value>{{ entry.tasks.length }}</template>
						</Badge>
						<Badge v-if="mandatoryCount(entry) > 0" color="warning" type="splitted" bright>
							<template #label>Mandatory</template>
							<template #value>{{ mandatoryCount(entry) }}</template>
						</Badge>
						<n-tag
							v-if="entry.match_field && entry.match_value"
							size="tiny"
							:bordered="false"
							type="success"
							:title="`Conditional: applies when ${entry.match_field} == ${entry.match_value}`"
						>
							{{ entry.match_field }} == {{ entry.match_value }}
						</n-tag>
						<n-tag v-for="tactic of mitreTactics(entry)" :key="tactic" size="tiny" :bordered="false">
							{{ tactic }}
						</n-tag>
					</div>
				</div>
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
import type { CaseTemplateLibraryEntry } from "@/types/incidentManagement/caseTemplates.d"
import { NAlert, NButton, NEmpty, NInput, NSpin, NTag, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"
import CaseTemplateLibraryImportModal from "./CaseTemplateLibraryImportModal.vue"

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

function mandatoryCount(entry: CaseTemplateLibraryEntry): number {
	return entry.tasks.filter(t => t.mandatory).length
}

function mitreTactics(entry: CaseTemplateLibraryEntry): string[] {
	const raw = entry.tags?.mitre_tactics
	if (!Array.isArray(raw)) return []
	return raw.filter((t): t is string => typeof t === "string")
}

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
			message.error(err.response?.data?.message || "Failed to load case-template library")
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
	} catch (err: any) {
		message.error(err.response?.data?.message || "Failed to refresh case-template library")
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

<style scoped lang="scss">
.library-card {
	display: flex;
	flex-direction: column;
	gap: 10px;
	padding: 12px;
	border: 1px solid var(--border-color);
	border-radius: var(--border-radius);
	background: var(--bg-default-color);
	transition:
		border-color 0.12s,
		box-shadow 0.12s;
}
.library-card:hover {
	border-color: rgba(var(--primary-color-rgb) / 0.5);
}
.library-card-name {
	font-weight: 600;
	color: var(--fg-default-color);
}
.library-card-meta {
	margin-top: auto;
}
</style>
