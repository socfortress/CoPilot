<template>
	<div>
		<CardEntity>
			<template #headerMain>
				<div class="text-default font-display text-lg font-semibold">
					{{ config.organization }}
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
								<p class="text-secondary mb-1 text-[10px] font-medium tracking-widest uppercase">
									Grade
								</p>
								<p
									v-if="config.last_audit_grade"
									class="font-mono text-4xl leading-none font-bold tracking-tight"
									:class="gradeTextClass"
								>
									{{ config.last_audit_grade }}
								</p>
								<p v-else class="text-tertiary font-mono text-3xl leading-none font-semibold">—</p>
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
									{{
										config.last_audit_at ? formatDate(config.last_audit_at, dFormats.datetime) : "—"
									}}
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
					<n-button type="primary" size="small" quaternary :loading="running" @click.stop="runAudit">
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
				</div>
			</template>
		</CardEntity>
		<n-card class="github-audit-card" hoverable @click="$emit('click', config)">
			<div class="flex items-start justify-between">
				<div class="flex-1">
					<div class="mb-2 flex items-center gap-2">
						<n-icon size="20" :color="config.enabled ? '#18a058' : '#999'">
							<Icon :name="GithubIcon" />
						</n-icon>
						<h3 class="m-0 text-lg font-semibold">{{ config.organization }}</h3>
						<n-tag v-if="!config.enabled" type="warning" size="small">Disabled</n-tag>
					</div>

					<div class="text-secondary mb-3 text-sm">
						<span>Customer: {{ config.customer_code }}</span>
					</div>

					<div class="flex gap-4 text-sm">
						<div v-if="config.last_audit_at" class="flex items-center gap-1">
							<n-icon><Icon :name="ClockIcon" /></n-icon>
							<span>Last audit: {{ formatDate(config.last_audit_at, dFormats.datetime) }}</span>
						</div>
						<div v-if="config.last_audit_grade" class="flex items-center gap-1">
							<span>Grade:</span>
							<GitHubAuditGradeBadge
								:grade="config.last_audit_grade"
								:score="config.last_audit_score ?? undefined"
							/>
						</div>
						<div v-if="config.auto_audit_enabled" class="flex items-center gap-1">
							<n-icon color="#18a058"><Icon :name="ScheduleIcon" /></n-icon>
							<span>Scheduled</span>
						</div>
					</div>
				</div>

				<div class="flex flex-col gap-2">
					<n-button type="primary" size="small" :loading="running" @click.stop="runAudit">
						<template #icon>
							<n-icon><Icon :name="PlayIcon" /></n-icon>
						</template>
						Run Audit
					</n-button>
					<n-button size="small" @click.stop="$emit('edit', config)">
						<template #icon>
							<n-icon><Icon :name="EditIcon" /></n-icon>
						</template>
						Edit
					</n-button>
				</div>
			</div>

			<n-divider v-if="config.last_audit_score !== null" style="margin: 12px 0" />

			<div v-if="config.last_audit_score !== null" class="audit-score-bar">
				<div class="mb-1 flex justify-between">
					<span class="text-sm">Security Score</span>
					<span class="text-sm font-semibold">{{ config.last_audit_score?.toFixed(1) }}%</span>
				</div>
				<n-progress
					type="line"
					:percentage="config.last_audit_score ?? 0"
					:status="scoreStatus"
					:show-indicator="false"
				/>
			</div>
		</n-card>
	</div>
</template>

<script setup lang="ts">
// TODO-FE: refactor
import type { GitHubAuditConfig } from "@/types/githubAudit.d"
import { NButton, NCard, NDivider, NIcon, NProgress, NTag, NTooltip, useMessage } from "naive-ui"
import { computed, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"
import CardEntity from "../common/cards/CardEntity.vue"
import GitHubAuditGradeBadge from "./GitHubAuditGradeBadge.vue"

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

const GithubIcon = "carbon:logo-github"
const ClockIcon = "carbon:time"
const ScheduleIcon = "carbon:calendar"
const PlayIcon = "carbon:play"
const EditIcon = "carbon:edit"

const message = useMessage()
const running = ref(false)
const dFormats = useSettingsStore().dateFormat

const scoreStatus = computed(() => {
	const score = props.config.last_audit_score ?? 0
	if (score >= 80) return "success"
	if (score >= 60) return "warning"
	return "error"
})

const gradeTextClass = computed(() => {
	const grade = props.config.last_audit_grade
	if (!grade) return ""
	if (grade === "A" || grade === "A+") return "text-success"
	if (grade.startsWith("B")) return "text-info"
	if (grade.startsWith("C")) return "text-warning"
	if (grade === "D" || grade === "D+" || grade === "F") return "text-error"
	return "text-tertiary"
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

<style scoped>
.github-audit-card {
	cursor: pointer;
	transition: all 0.2s ease;
}

.github-audit-card:hover {
	transform: translateY(-2px);
}

.text-secondary {
	color: var(--text-color-3);
}
</style>
