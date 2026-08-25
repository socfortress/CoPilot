<template>
	<div class="page flex flex-col gap-4">
		<!-- Header -->
		<div class="flex flex-wrap items-center gap-3">
			<n-button quaternary circle size="small" title="Back to searches" @click="goBack">
				<template #icon><Icon :name="BackIcon" :size="18" /></template>
			</n-button>
			<Icon :name="EditorIcon" :size="22" />
			<span class="text-lg font-semibold">Detection Rule Editor</span>
			<n-tag size="small" round :bordered="false" type="info">Graylog-only</n-tag>

			<!-- live status -->
			<n-tag v-if="result" size="small" round :bordered="false" :type="result.valid ? 'success' : 'error'">
				<template #icon><Icon :name="result.valid ? OkIcon : ErrIcon" :size="14" /></template>
				{{ result.valid ? "Valid" : `${result.error_count} error${result.error_count === 1 ? "" : "s"}` }}
			</n-tag>
			<n-tag v-if="result && result.warning_count" size="small" round :bordered="false" type="warning">
				{{ result.warning_count }} warning{{ result.warning_count === 1 ? "" : "s" }}
			</n-tag>
			<n-spin v-if="validating" :size="14" />

			<div class="grow" />
			<n-button size="small" secondary @click="loadSimple">
				<template #icon><Icon :name="TemplateIcon" :size="16" /></template>
				New simple rule
			</n-button>
			<n-button size="small" secondary @click="loadAggregation">
				<template #icon><Icon :name="AggIcon" :size="16" /></template>
				New aggregation rule
			</n-button>
			<n-tooltip>
				<template #trigger>
					<n-button size="small" secondary :disabled="!yamlText.trim()" @click="copyYaml">
						<template #icon><Icon :name="CopyIcon" :size="16" /></template>
					</n-button>
				</template>
				Copy YAML
			</n-tooltip>
			<n-button size="small" type="primary" :disabled="!yamlText.trim()" @click="showBacktest = true">
				<template #icon><Icon :name="BacktestIcon" :size="16" /></template>
				Backtest
			</n-button>
			<n-button size="small" type="primary" :disabled="!result?.valid">
				<template #icon><Icon :name="PublishIcon" :size="16" /></template>
				Publish (soon)
			</n-button>
		</div>

		<div class="flex min-h-0 grow flex-col gap-4 lg:flex-row">
			<!-- Left: YAML source -->
			<div class="flex min-w-0 grow flex-col gap-2 lg:w-1/2">
				<div class="flex items-center gap-2">
					<span class="text-secondary text-xs font-medium">Rule YAML</span>
					<n-tag size="tiny" round :bordered="false">
						<template #icon><Icon :name="LockIcon" :size="11" /></template>
						required fields are locked
					</n-tag>
				</div>
				<div class="border-default overflow-hidden rounded-lg border" :style="{ height: '62vh' }">
					<RuleYamlEditor ref="editorRef" v-model:code="yamlText" @blocked="onBlocked" />
				</div>
			</div>

			<!-- Right: validation + Graylog syntax reference -->
			<div class="flex min-w-0 grow flex-col gap-2 lg:w-1/2">
				<n-tabs v-model:value="rightTab" type="segment" size="small">
					<n-tab-pane name="validation" tab="Validation">
						<div class="border-default overflow-auto rounded-lg border p-3" :style="{ height: '58vh' }">
							<!-- valid hero -->
							<div
								v-if="result?.valid && !result.warning_count"
								class="flex flex-col items-center justify-center gap-2 py-16 text-center"
							>
								<Icon :name="OkIcon" :size="40" class="text-green-500" />
								<span class="text-base font-semibold">Looks good</span>
								<span class="text-secondary max-w-xs text-sm">
									No structural, lint, or Graylog-query issues. Reference integrity and per-tenant field
									checks come next.
								</span>
							</div>

							<n-empty v-else-if="!result && !validating" description="Start typing to validate." class="mt-10" />

							<div v-else class="flex flex-col gap-4">
								<!-- errors -->
								<div v-if="errorFindings.length" class="flex flex-col gap-2">
									<h4 class="section-title">Errors ({{ errorFindings.length }})</h4>
									<div
										v-for="(f, i) of errorFindings"
										:key="`e${i}`"
										class="finding-row"
										:class="{ clickable: !!f.line }"
										@click="jumpTo(f)"
									>
										<n-tag size="tiny" round :bordered="false" type="error">error</n-tag>
										<div class="flex min-w-0 grow flex-col gap-0.5">
											<div class="flex items-center gap-2">
												<code class="text-xs">{{ f.code }}</code>
												<span v-if="f.line" class="text-secondary text-xs">line {{ f.line }}</span>
												<span v-else-if="f.path" class="text-secondary text-xs">{{ f.path }}</span>
											</div>
											<span class="text-sm break-words">{{ f.message }}</span>
										</div>
										<Icon v-if="f.line" :name="JumpIcon" :size="14" class="text-secondary mt-1 shrink-0" />
									</div>
								</div>

								<!-- warnings -->
								<div v-if="warningFindings.length" class="flex flex-col gap-2">
									<h4 class="section-title">Warnings ({{ warningFindings.length }})</h4>
									<div
										v-for="(f, i) of warningFindings"
										:key="`w${i}`"
										class="finding-row"
										:class="{ clickable: !!f.line }"
										@click="jumpTo(f)"
									>
										<n-tag size="tiny" round :bordered="false" type="warning">warning</n-tag>
										<div class="flex min-w-0 grow flex-col gap-0.5">
											<div class="flex items-center gap-2">
												<code class="text-xs">{{ f.code }}</code>
												<span v-if="f.line" class="text-secondary text-xs">line {{ f.line }}</span>
												<span v-else-if="f.path" class="text-secondary text-xs">{{ f.path }}</span>
											</div>
											<span class="text-sm break-words">{{ f.message }}</span>
										</div>
										<Icon v-if="f.line" :name="JumpIcon" :size="14" class="text-secondary mt-1 shrink-0" />
									</div>
								</div>
							</div>
						</div>
					</n-tab-pane>
					<n-tab-pane name="syntax" tab="Graylog syntax">
						<div class="border-default overflow-auto rounded-lg border p-3" :style="{ height: '58vh' }">
							<GraylogSyntaxReference />
						</div>
					</n-tab-pane>
				</n-tabs>
			</div>
		</div>

		<BacktestModal v-model:show="showBacktest" :yaml="yamlText" />
	</div>
</template>

<script setup lang="ts">
import type { LintFinding, ValidateRuleResponse } from "@/types/copilot-searches"
import { watchDebounced } from "@vueuse/core"
import { NButton, NEmpty, NSpin, NTabPane, NTabs, NTag, NTooltip, useMessage } from "naive-ui"
import { computed, onMounted, ref } from "vue"
import { useRouter } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import BacktestModal from "@/components/copilotSearches/BacktestModal.vue"
import GraylogSyntaxReference from "@/components/copilotSearches/GraylogSyntaxReference.vue"
import RuleYamlEditor from "@/components/copilotSearches/RuleYamlEditor.vue"
import { getApiErrorMessage } from "@/utils"

const EditorIcon = "carbon:code"
const BackIcon = "carbon:arrow-left"
const OkIcon = "carbon:checkmark-filled"
const ErrIcon = "carbon:warning-alt-filled"
const TemplateIcon = "carbon:document-add"
const BacktestIcon = "carbon:chart-line"
const PublishIcon = "carbon:cloud-upload"
const LockIcon = "carbon:locked"
const CopyIcon = "carbon:copy"
const AggIcon = "carbon:chart-histogram"
const JumpIcon = "carbon:arrow-right"

const message = useMessage()
const router = useRouter()

function goBack() {
	router.push({ name: "CopilotSearches" })
}

function onBlocked(key: string) {
	message.warning(`"${key}" is a required field and can't be removed — edit its value instead.`)
}

const yamlText = ref<string>("")
const result = ref<ValidateRuleResponse | null>(null)
const validating = ref(false)
const rightTab = ref<"validation" | "syntax">("validation")
const showBacktest = ref(false)
const editorRef = ref<InstanceType<typeof RuleYamlEditor> | null>(null)

// Findings grouped by level, each sorted by line.
const byLine = (a: LintFinding, b: LintFinding) => (a.line ?? 1e9) - (b.line ?? 1e9)
const errorFindings = computed<LintFinding[]>(() =>
	(result.value?.findings || []).filter(f => f.level === "error").sort(byLine)
)
const warningFindings = computed<LintFinding[]>(() =>
	(result.value?.findings || []).filter(f => f.level === "warning").sort(byLine)
)

function jumpTo(f: LintFinding) {
	if (f.line) editorRef.value?.goToLine(f.line)
}

async function copyYaml() {
	if (!yamlText.value.trim()) return
	try {
		await navigator.clipboard.writeText(yamlText.value)
		message.success("Rule YAML copied to clipboard")
	} catch {
		message.error("Couldn't copy to clipboard")
	}
}

// --- templates ---
type TemplateKind = "none" | "disabled" | "enabled"

function makeTemplate(agg: TemplateKind): string {
	const id = (globalThis.crypto?.randomUUID?.() as string) || "00000000-0000-0000-0000-000000000000"
	const today = new Date().toISOString().slice(0, 10)
	const base = `name: New Detection Rule
id: ${id}
version: 1
schema_version: "1.0"
date: "${today}"
author: SOCFortress LLC
description: >
  Describe what this rule detects and why it matters.
data_source:
  - Windows Security Event Log
how_to_implement: >
  What must be collected or enabled for this rule to fire.
known_false_positives: >
  Known benign activity that can trigger this, and how to tune it out.
response:
  risk_score: 50
  severity: medium
tags:
  asset_type: Endpoint
  mitre_attack_id:
    - T1098
  custom_tags:
    - example
  product:
    - Wazuh
  security_domain: endpoint
graylog:
  query: data_win_system_eventID:"4706"
`
	if (agg === "none") return base
	const enabled = agg === "enabled"
	return `${base}${enabled ? "" : "# Optional — only for threshold / aggregation rules (e.g. \"N events per user in 10m\").\n# Leave enabled: false (or delete this whole block) for a simple match rule.\n"}aggregation:
  enabled: ${enabled}
  function: count            # count | distinct_count
  field: null                # required only when function is distinct_count
  group_by:
    - data_win_eventdata_targetUserName
  window: 10m
  threshold: 30
  condition: ">"             # one of  >  >=  <  <=  ==
`
}

function loadTemplate(kind: TemplateKind) {
	const text = makeTemplate(kind)
	// Push straight into the editor so a fresh template always loads, even when the
	// current one is modified/emptied (bypasses the required-field lock cleanly).
	if (editorRef.value?.setContent) editorRef.value.setContent(text)
	else yamlText.value = text
}
const loadSimple = () => loadTemplate("none")
const loadAggregation = () => loadTemplate("enabled")

async function validate() {
	if (!yamlText.value.trim()) {
		result.value = null
		return
	}
	validating.value = true
	try {
		const res = await Api.copilotSearches.validateRule({ yaml: yamlText.value })
		result.value = res.data
	} catch (err) {
		message.error(getApiErrorMessage(err as any) || "Validation request failed.")
	} finally {
		validating.value = false
	}
}

watchDebounced(yamlText, validate, { debounce: 400 })

onMounted(() => {
	yamlText.value = makeTemplate("disabled")
})
</script>

<style scoped>
.section-title {
	font-size: 11px;
	font-weight: 600;
	letter-spacing: 0.06em;
	text-transform: uppercase;
	color: var(--n-text-color-3, #888);
}
.finding-row {
	display: flex;
	align-items: flex-start;
	gap: 12px;
	border-radius: 8px;
	padding: 12px;
	background: var(--bg-secondary-color, rgba(128, 128, 128, 0.08));
	transition:
		background 0.15s ease,
		transform 0.05s ease;
}
.finding-row.clickable {
	cursor: pointer;
}
.finding-row.clickable:hover {
	background: var(--bg-body-color, rgba(128, 128, 128, 0.16));
	filter: brightness(1.05);
}
</style>
