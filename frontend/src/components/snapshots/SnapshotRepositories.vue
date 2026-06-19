<template>
	<div class="flex flex-col gap-4">
		<n-alert type="info" show-icon>
			<template #header>Repository Registration Required</template>
			Snapshot repositories must be manually registered in your Wazuh Indexer cluster.
			<a
				href="https://docs.opensearch.org/2.19/tuning-your-cluster/availability-and-recovery/snapshots/snapshot-restore/"
				target="_blank"
			>
				View the documentation
			</a>
			for instructions on how to register a snapshot repository.
		</n-alert>

		<n-spin :show="loading">
			<div v-if="repositories.length" class="flex flex-col gap-3">
				<CardEntity
					v-for="repo in repositories"
					:key="repo.name"
					size="small"
					embedded
					header-box-class="text-default! items-start"
					:status="repo.settings.readonly ? 'warning' : undefined"
				>
					<template #headerMain>
						<span class="font-mono text-sm font-semibold">{{ repo.name }}</span>
					</template>

					<template #headerExtra>
						<div class="flex flex-wrap items-center justify-end gap-2">
							<Badge type="splitted" bright size="small" :color="typeBadgeColor(repo.type)">
								<template #label>
									<Icon :name="typeIcon(repo.type)" :size="12" />
									Type
								</template>
								<template #value>{{ repo.type }}</template>
							</Badge>
							<Badge v-if="repo.settings.readonly" type="splitted" bright size="small" color="warning">
								<template #label>Readonly</template>
							</Badge>
						</div>
					</template>

					<template #default>
						<div class="flex flex-wrap gap-2">
							<Badge
								v-for="(value, key) in repo.settings"
								:key="`${repo.name}-${String(key)}`"
								type="splitted"
								size="small"
							>
								<template #label>{{ formatSettingLabel(String(key)) }}</template>
								<template #value>{{ formatSettingValue(value) }}</template>
							</Badge>
						</div>
					</template>
				</CardEntity>
			</div>
			<n-empty v-else description="No snapshot repositories found" class="min-h-48 justify-center" />
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { BadgeColor } from "@/components/common/Badge.vue"
import type { SafeAny } from "@/types/common"
import type { SnapshotRepository } from "@/types/snapshots"
import { NAlert, NEmpty, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"

const emit = defineEmits<{
	loaded: [repositories: SnapshotRepository[]]
}>()

const FolderIcon = "carbon:folder"
const CloudIcon = "carbon:cloud"

const UNDERSCORE_REGEX = /_/g

const message = useMessage()
const loading = ref(false)
const repositories = ref<SnapshotRepository[]>([])

function typeBadgeColor(type: string): BadgeColor | undefined {
	if (type === "s3") return "primary"
	if (type === "fs") return "success"
	return undefined
}

function typeIcon(type: string) {
	if (type === "s3") return CloudIcon
	return FolderIcon
}

function formatSettingLabel(key: string) {
	return key.replace(UNDERSCORE_REGEX, " ")
}

function formatSettingValue(value: SafeAny) {
	if (typeof value === "boolean") return value ? "true" : "false"
	if (value === null || value === undefined) return "-"
	return String(value)
}

async function fetchRepositories() {
	loading.value = true
	try {
		const response = await Api.snapshots.getRepositories()
		if (response.data.success) {
			repositories.value = response.data.repositories
		} else {
			message.error(response.data.message)
			repositories.value = []
		}
	} catch (error: any) {
		message.error(error.message || "Failed to fetch repositories")
		repositories.value = []
	} finally {
		loading.value = false
		emit("loaded", repositories.value)
	}
}

onBeforeMount(() => {
	fetchRepositories()
})
</script>
