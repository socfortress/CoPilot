<template>
	<div class="flex flex-col gap-4">
		<div class="flex items-center gap-2">
			<n-select
				v-model:value="selectedRepository"
				:options="repositoryOptions"
				placeholder="Select Repository"
				class="max-w-50"
				size="small"
				:consistent-menu-width="false"
				@update:value="fetchSnapshots"
			/>
			<n-button type="primary" size="small" :disabled="!selectedRepository" @click="showCreateModal = true">
				<template #icon>
					<Icon :name="AddIcon" :size="16" />
				</template>
				Create Snapshot
			</n-button>
		</div>

		<n-spin :show="loading">
			<div v-if="selectedRepository">
				<div v-if="snapshots.length" class="flex flex-col gap-3">
					<CardEntity
						v-for="snapshot in snapshots"
						:key="snapshot.snapshot"
						size="small"
						embedded
						header-box-class="text-default! items-start"
						:status="snapshotCardStatus(snapshot.state)"
					>
						<template #headerMain>
							<span class="font-mono text-sm font-semibold">{{ snapshot.snapshot }}</span>
						</template>

						<template #headerExtra>
							<Badge type="splitted" bright size="small" :color="snapshotStateBadgeColor(snapshot.state)">
								<template #label>State</template>
								<template #value>{{ snapshot.state }}</template>
							</Badge>
						</template>

						<template #default>
							<div class="flex flex-wrap gap-2">
								<Badge type="splitted" size="small">
									<template #label>Indices</template>
									<template #value>{{ snapshot.indices.length }}</template>
								</Badge>
								<Badge v-if="snapshot.version" type="splitted" size="small">
									<template #label>Version</template>
									<template #value>{{ snapshot.version }}</template>
								</Badge>
								<Badge
									v-if="snapshot.include_global_state"
									type="splitted"
									size="small"
									color="primary"
								>
									<template #label>Global state</template>
								</Badge>
								<Badge v-if="snapshot.failures.length > 0" type="splitted" size="small" color="danger">
									<template #label>Failures</template>
									<template #value>{{ snapshot.failures.length }}</template>
								</Badge>
							</div>
						</template>

						<template #footerMain>
							<div class="flex flex-wrap items-center gap-2">
								<Badge type="splitted" bright size="small">
									<template #label>Start</template>
									<template #value>{{ formatSnapshotTime(snapshot.start_time) }}</template>
								</Badge>
								<Badge type="splitted" bright size="small">
									<template #label>End</template>
									<template #value>{{ formatSnapshotTime(snapshot.end_time) }}</template>
								</Badge>
								<Badge type="splitted" bright size="small">
									<template #label>Duration</template>
									<template #value>{{ formatDuration(snapshot.duration_in_millis) }}</template>
								</Badge>
								<Badge v-if="snapshot.shards?.total" type="splitted" size="small">
									<template #label>Shards</template>
									<template #value>{{ formatShards(snapshot.shards) }}</template>
								</Badge>
							</div>
						</template>

						<template #footerExtra>
							<n-button size="small" type="primary" secondary @click="openRestoreModal(snapshot)">
								<template #icon>
									<Icon :name="RestoreIcon" :size="14" />
								</template>
								Restore
							</n-button>
						</template>
					</CardEntity>
				</div>

				<n-empty v-else description="No snapshots found in this repository" class="min-h-48 justify-center" />
			</div>

			<n-empty v-else description="Select a repository to view snapshots" class="min-h-48 justify-center" />
		</n-spin>

		<n-modal v-model:show="showCreateModal" preset="card" title="Create Snapshot" class="max-w-160!">
			<CreateSnapshotForm
				:repository="selectedRepository"
				@success="onSnapshotCreated"
				@cancel="showCreateModal = false"
			/>
		</n-modal>

		<n-modal v-model:show="showRestoreModal" preset="card" title="Restore Snapshot">
			<RestoreSnapshotForm
				:repository="selectedRepository"
				:snapshot="selectedSnapshot"
				@success="onSnapshotRestored"
				@cancel="showRestoreModal = false"
			/>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { SelectOption } from "naive-ui"
import type { BadgeColor } from "@/components/common/Badge.vue"
import type { SnapshotInfo, SnapshotRepository } from "@/types/snapshots"
import { NButton, NEmpty, NModal, NSelect, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"
import CreateSnapshotForm from "./CreateSnapshotForm.vue"
import RestoreSnapshotForm from "./RestoreSnapshotForm.vue"

const { repositories: repositoriesProp } = defineProps<{
	repositories?: SnapshotRepository[]
}>()

const dFormats = useSettingsStore().dateFormat
const AddIcon = "carbon:add"
const RestoreIcon = "carbon:reset"

const message = useMessage()
const loading = ref(false)
const repositories = ref<SnapshotRepository[]>([])
const selectedRepository = ref<string | null>(null)
const snapshots = ref<SnapshotInfo[]>([])
const showCreateModal = ref(false)
const showRestoreModal = ref(false)
const selectedSnapshot = ref<SnapshotInfo | null>(null)

const repositoryOptions = computed<SelectOption[]>(() =>
	repositories.value.map(repo => ({
		label: repo.name,
		value: repo.name
	}))
)

function snapshotCardStatus(state: string) {
	if (state === "SUCCESS") return "success"
	if (state === "FAILED") return "error"
	if (state === "IN_PROGRESS" || state === "PARTIAL") return "warning"
	return undefined
}

function snapshotStateBadgeColor(state: string): BadgeColor | undefined {
	if (state === "SUCCESS") return "success"
	if (state === "FAILED") return "danger"
	if (state === "IN_PROGRESS" || state === "PARTIAL") return "warning"
	return "primary"
}

function formatSnapshotTime(value?: string) {
	if (!value) return "-"
	return formatDate(value, dFormats.datetime, { tz: true })
}

function formatDuration(ms?: number) {
	if (!ms) return "-"
	const seconds = Math.floor(ms / 1000)
	if (seconds < 60) return `${seconds}s`
	const minutes = Math.floor(seconds / 60)
	return `${minutes}m ${seconds % 60}s`
}

function formatShards(shards: Record<string, unknown>) {
	const total = shards.total
	const successful = shards.successful
	const failed = shards.failed

	if (typeof total === "number" && typeof successful === "number") {
		if (typeof failed === "number" && failed > 0) return `${successful}/${total} (${failed} failed)`
		return `${successful}/${total}`
	}

	return String(total ?? "-")
}

function openRestoreModal(snapshot: SnapshotInfo) {
	selectedSnapshot.value = snapshot
	showRestoreModal.value = true
}

function applyRepositories(repos: SnapshotRepository[]) {
	repositories.value = repos

	if (repos.length === 0) {
		selectedRepository.value = null
		snapshots.value = []
		return
	}

	if (!selectedRepository.value || !repos.some(repo => repo.name === selectedRepository.value)) {
		selectedRepository.value = repos[0].name
		fetchSnapshots()
	}
}

async function fetchRepositories() {
	try {
		const response = await Api.snapshots.getRepositories()
		if (response.data.success) {
			applyRepositories(response.data.repositories)
		} else {
			message.error(response.data.message)
			applyRepositories([])
		}
	} catch (error: any) {
		message.error(error.message || "Failed to fetch repositories")
		applyRepositories([])
	}
}

async function initRepositories() {
	if (repositoriesProp?.length) {
		applyRepositories(repositoriesProp)
		return
	}

	await fetchRepositories()
}

watch(
	() => repositoriesProp,
	repos => {
		if (repos?.length) applyRepositories(repos)
	},
	{ deep: true }
)

async function fetchSnapshots() {
	if (!selectedRepository.value) return

	loading.value = true
	try {
		const response = await Api.snapshots.listSnapshots(selectedRepository.value)
		if (response.data.success) {
			snapshots.value = response.data.snapshots
		} else {
			message.error(response.data.message)
			snapshots.value = []
		}
	} catch (error: any) {
		message.error(error.message || "Failed to fetch snapshots")
		snapshots.value = []
	} finally {
		loading.value = false
	}
}

function onSnapshotCreated() {
	showCreateModal.value = false
	fetchSnapshots()
	message.success("Snapshot creation initiated")
}

function onSnapshotRestored() {
	showRestoreModal.value = false
	message.success("Snapshot restoration initiated")
}

onBeforeMount(() => {
	initRepositories()
})
</script>
