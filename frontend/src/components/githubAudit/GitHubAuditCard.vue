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
			<div class="flex items-center gap-6">
				<n-progress
					type="circle"
					:percentage="config.last_audit_score ?? 0"
					:status="scoreStatus"
					gap-position="bottom"
				>
					<div class="flex flex-col items-center justify-between gap-1 text-center">
						<span class="text-xs">Security Score</span>
					</div>
				</n-progress>
				<div class="flex min-w-0 flex-1 flex-col gap-3">
					<div class="flex items-end justify-between gap-3">
						<div class="min-w-0">
							<p class="text-secondary mb-1 text-[10px] font-medium tracking-widest uppercase">Grade</p>
							<GitHubAuditGradeLabel :grade="config.last_audit_grade" />
						</div>
						<p
							v-if="config.last_audit_score != null"
							class="text-secondary shrink-0 font-mono text-xs tabular-nums"
						>
							{{ config.last_audit_score.toFixed(1) }}%
						</p>
					</div>

					<dl class="border-border flex flex-col gap-2 border-t pt-3">
						<div class="flex items-baseline justify-between gap-3">
							<dt class="text-secondary shrink-0 text-[10px] tracking-wider uppercase">Customer</dt>
							<dd class="text-default min-w-0 truncate font-mono text-xs">
								{{ config.customer_code }}
							</dd>
						</div>
						<div class="flex items-baseline justify-between gap-3">
							<dt class="text-secondary shrink-0 text-[10px] tracking-wider uppercase">Last audit</dt>
							<dd class="text-default min-w-0 truncate text-right font-mono text-xs tabular-nums">
								{{ config.last_audit_at ? formatDate(config.last_audit_at, dFormats.datetime) : "—" }}
							</dd>
						</div>
					</dl>
				</div>
			</div>
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
import { NButton, NProgress, NTag, NTooltip, useMessage } from "naive-ui"
import { computed, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"
import CardEntity from "../common/cards/CardEntity.vue"
import GitHubAuditGradeLabel from "./GitHubAuditGradeLabel.vue"

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
const dFormats = useSettingsStore().dateFormat

const scoreStatus = computed(() => {
	const score = props.config.last_audit_score ?? 0
	if (score >= 80) return "success"
	if (score >= 60) return "warning"
	return "error"
})

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
