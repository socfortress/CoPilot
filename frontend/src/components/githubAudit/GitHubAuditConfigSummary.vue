<template>
	<div class="flex items-center gap-6">
		<n-progress
			v-if="showScore"
			type="circle"
			:percentage="config.last_audit_score ?? 0"
			:status="scoreStatus"
			gap-position="bottom"
		>
			<div class="flex flex-col items-center justify-between gap-1 text-center">
				<span class="text-xs">Security Score</span>
			</div>
		</n-progress>

		<div v-if="showGrade || hasMetaFields" class="flex min-w-0 flex-1 flex-col gap-3">
			<div v-if="showGrade" class="flex items-end justify-between gap-3">
				<div class="min-w-0">
					<p class="text-secondary mb-1 text-[10px] font-medium tracking-widest uppercase">Grade</p>
					<GitHubAuditGradeLabel :grade="config.last_audit_grade" />
				</div>
				<p
					v-if="showScore && config.last_audit_score != null"
					class="text-secondary shrink-0 font-mono text-xs tabular-nums"
				>
					{{ config.last_audit_score.toFixed(1) }}%
				</p>
			</div>

			<dl v-if="hasMetaFields" class="border-border flex flex-col gap-2" :class="{ 'border-t pt-3': showGrade }">
				<div v-if="showCustomer" class="flex items-baseline justify-between gap-3">
					<dt class="text-secondary shrink-0 text-[10px] tracking-wider uppercase">Customer</dt>
					<dd class="text-default min-w-0 truncate font-mono text-xs">
						{{ config.customer_code }}
					</dd>
				</div>
				<div v-if="showOrganization" class="flex items-baseline justify-between gap-3">
					<dt class="text-secondary shrink-0 text-[10px] tracking-wider uppercase">Organization</dt>
					<dd class="text-default min-w-0 truncate font-mono text-xs">
						{{ config.organization }}
					</dd>
				</div>
				<div v-if="showLastAudit" class="flex items-baseline justify-between gap-3">
					<dt class="text-secondary shrink-0 text-[10px] tracking-wider uppercase">Last audit</dt>
					<dd class="text-default min-w-0 truncate text-right font-mono text-xs tabular-nums">
						{{ config.last_audit_at ? formatDate(config.last_audit_at, dFormats.datetime) : "—" }}
					</dd>
				</div>
				<div v-if="showTokenType" class="flex items-baseline justify-between gap-3">
					<dt class="text-secondary shrink-0 text-[10px] tracking-wider uppercase">Token type</dt>
					<dd class="text-default min-w-0 truncate text-right font-mono text-xs">
						{{ tokenTypeLabel }}
					</dd>
				</div>
			</dl>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { GitHubAuditConfig } from "@/types/githubAudit.d"
import { NProgress } from "naive-ui"
import { computed } from "vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"
import GitHubAuditGradeLabel from "./GitHubAuditGradeLabel.vue"

export type GitHubAuditConfigSummaryMetaFields = "all" | "card" | "none"

const props = withDefaults(
	defineProps<{
		config: GitHubAuditConfig
		showScore?: boolean
		showGrade?: boolean
		metaFields?: GitHubAuditConfigSummaryMetaFields
	}>(),
	{
		showScore: true,
		showGrade: true,
		metaFields: "all"
	}
)

const dFormats = useSettingsStore().dateFormat

const showCustomer = computed(() => props.metaFields === "all" || props.metaFields === "card")
const showOrganization = computed(() => props.metaFields === "all")
const showLastAudit = computed(() => props.metaFields === "all" || props.metaFields === "card")
const showTokenType = computed(() => props.metaFields === "all")

const hasMetaFields = computed(
	() => showCustomer.value || showOrganization.value || showLastAudit.value || showTokenType.value
)

const scoreStatus = computed(() => {
	const score = props.config.last_audit_score ?? 0
	if (score >= 80) return "success"
	if (score >= 60) return "warning"
	return "error"
})

const tokenTypeLabel = computed(() => (props.config.token_type === "pat" ? "Personal Access Token" : "GitHub App"))
</script>
