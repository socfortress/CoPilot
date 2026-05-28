<template>
	<CardEntity>
		<template #headerMain>
			<div class="flex items-center gap-3">
				<Icon name="codicon:organization" :size="20" />

				<div class="text-default font-display text-lg font-semibold">
					{{ config.organization }}
				</div>
			</div>
		</template>
		<template #headerExtra>
			<div class="flex items-center justify-end gap-2">
				<n-tag v-if="config.enabled" type="success" size="small">Enabled</n-tag>
				<n-tag v-else type="error" size="small">Disabled</n-tag>

				<n-tag v-if="config.auto_audit_enabled" type="success" size="small">Scheduled</n-tag>
				<n-tag v-else type="error" size="small">Not scheduled</n-tag>
			</div>
		</template>
		<template #default>
			<GitHubAuditConfigSummary :config meta-fields="card" />
		</template>
		<template #footerMain>
			<div class="border-border divide-border grid grid-cols-4 divide-x rounded-md border">
				<n-tooltip v-for="flag in includeFlags" :key="flag.key" class="px-2! py-1!">
					<template #trigger>
						<div class="flex flex-col items-center justify-center gap-0 px-1 py-0.5">
							<span class="text-xs">{{ flag.shortLabel }}</span>
							<Icon
								:name="config[flag.key] ? 'carbon:checkmark' : 'carbon:close'"
								:class="config[flag.key] ? 'text-success' : 'text-error'"
							/>
						</div>
					</template>
					<span class="text-xs">{{ flag.label }}</span>
				</n-tooltip>
			</div>
		</template>
		<template #footerExtra>
			<div class="flex flex-wrap items-center justify-end gap-2">
				<n-button size="small" quaternary :loading="running" @click.stop="runAudit">
					<template #icon>
						<Icon :name="PlayIcon" />
					</template>
					Run Audit
				</n-button>
				<n-button size="small" @click.stop="$emit('edit', config)">
					<template #icon>
						<Icon :name="EditIcon" />
					</template>
					Edit
				</n-button>
				<n-button size="small" type="primary" secondary @click.stop="$emit('click', config)">
					<template #icon>
						<Icon :name="DetailIcon" />
					</template>
					View Details
				</n-button>
			</div>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { GitHubAuditConfig } from "@/types/githubAudit.d"
import { NButton, NTag, NTooltip, useMessage } from "naive-ui"
import { ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import CardEntity from "../common/cards/CardEntity.vue"
import GitHubAuditConfigSummary from "./GitHubAuditConfigSummary.vue"

type IncludeFlagKey = "include_archived_repos" | "include_members" | "include_repos" | "include_workflows"

const props = defineProps<{
	config: GitHubAuditConfig
}>()
const emit = defineEmits<{
	(e: "click", config: GitHubAuditConfig): void
	(e: "edit", config: GitHubAuditConfig): void
	(e: "audit-complete"): void
}>()

const includeFlags: { key: IncludeFlagKey; shortLabel: string; label: string }[] = [
	{ key: "include_archived_repos", shortLabel: "A", label: "Include archived repos" },
	{ key: "include_members", shortLabel: "M", label: "Include members" },
	{ key: "include_repos", shortLabel: "R", label: "Include repos" },
	{ key: "include_workflows", shortLabel: "W", label: "Include workflows" }
]

const PlayIcon = "carbon:play"
const EditIcon = "carbon:edit"
const DetailIcon = "carbon:view"

const message = useMessage()
const running = ref(false)

async function runAudit() {
	running.value = true
	try {
		await Api.githubAudit.runAuditFromConfig(props.config.id)
		message.success("Audit completed successfully")
		emit("audit-complete")
	} catch (error: any) {
		message.error(error.response?.data?.detail || "Failed to run audit")
	} finally {
		running.value = false
	}
}
</script>
