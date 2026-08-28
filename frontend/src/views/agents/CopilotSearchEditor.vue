<template>
	<div class="page page-wrapped page-without-footer editor-page flex flex-col">
		<!-- Page header — identity, live validation status, rule-level actions -->
		<header class="editor-head">
			<n-button quaternary circle size="small" title="Back to searches" @click="goBack">
				<template #icon><Icon :name="BackIcon" :size="18" /></template>
			</n-button>

			<div class="editor-head__title">
				<Icon :name="EditorIcon" :size="20" />
				<h1>Detection Rule Editor</h1>
				<n-tag size="small" round :bordered="false" type="info">Graylog-only</n-tag>
			</div>

			<div class="editor-head__status">
				<n-spin v-if="validating" :size="14" />
				<template v-else-if="result">
					<n-tag size="small" round :bordered="false" :type="result.valid ? 'success' : 'error'">
						<template #icon>
							<Icon :name="result.valid ? OkIcon : ErrIcon" :size="12" class="ml-1" />
						</template>
						{{
							result.valid ? "Valid" : `${result.error_count} error${result.error_count === 1 ? "" : "s"}`
						}}
					</n-tag>
					<n-tag v-if="result.warning_count" size="small" round :bordered="false" type="warning">
						{{ result.warning_count }} warning{{ result.warning_count === 1 ? "" : "s" }}
					</n-tag>
				</template>
			</div>

			<div class="grow" />

			<div class="flex items-center gap-2">
				<n-button size="small" secondary :disabled="!yamlText.trim()" @click="showBacktest = true">
					<template #icon><Icon :name="BacktestIcon" :size="16" /></template>
					Backtest
				</n-button>
				<n-button size="small" type="primary" :disabled="!result?.valid" @click="showPublish = true">
					<template #icon><Icon :name="PublishIcon" :size="16" /></template>
					Publish
				</n-button>
			</div>
		</header>

		<!-- Workspace — a single box split into the editor and the reference side -->
		<div class="workspace">
			<!-- Authoring side -->
			<section class="workspace__pane workspace__pane--main">
				<div class="workspace__toolbar @container">
					<div class="toolbar__group">
						<Icon :name="YamlIcon" :size="15" class="toolbar__icon" />
						<span class="toolbar__title leading-none">Rule YAML</span>
						<n-tooltip>
							<template #trigger>
								<span class="toolbar__hint">
									<Icon :name="LockIcon" :size="13" />
								</span>
							</template>
							Required schema fields are locked — edit their values, not the keys
						</n-tooltip>
					</div>

					<div class="grow" />

					<div class="toolbar__group">
						<span class="toolbar__label leading-none">Template</span>
						<n-button-group size="tiny">
							<n-tooltip class="px-2! py-1! text-sm!">
								<template #trigger>
									<n-button secondary @click="loadSimple">
										<div class="flex items-center gap-1.5">
											<Icon :name="TemplateIcon" :size="14" />
											<span class="hidden @lg:block">Sample rule</span>
										</div>
									</n-button>
								</template>
								Start a new simple match rule — replaces the editor content
							</n-tooltip>
							<n-tooltip class="px-2! py-1! text-sm!">
								<template #trigger>
									<n-button secondary @click="loadAggregation">
										<div class="flex items-center gap-1.5">
											<Icon :name="AggIcon" :size="14" />
											<span class="hidden @lg:block">New threshold rule</span>
										</div>
									</n-button>
								</template>
								Start a new threshold / aggregation rule — replaces the editor content
							</n-tooltip>
						</n-button-group>

						<span class="toolbar__divider" />

						<n-tooltip class="px-2! py-1! text-sm!">
							<template #trigger>
								<n-button size="tiny" secondary :disabled="!yamlText.trim()" @click="copyYaml">
									<template #icon><Icon :name="CopyIcon" :size="14" /></template>
								</n-button>
							</template>
							Copy YAML
						</n-tooltip>
					</div>
				</div>

				<div class="workspace__content">
					<RuleYamlEditor ref="editorRef" v-model:code="yamlText" @blocked="onBlocked" />
				</div>
			</section>

			<!-- Reference side — validation findings and Graylog syntax -->
			<aside class="workspace__pane workspace__pane--aside" :class="{ 'is-fit': rightTab === 'validation' }">
				<n-tabs v-model:value="rightTab" type="segment" size="small" class="aside-tabs">
					<n-tab-pane name="validation" tab="Validation">
						<n-scrollbar trigger="none" class="h-full">
							<div class="findings">
								<div v-if="result?.valid && !result.warning_count" class="findings__hero">
									<Icon :name="OkIcon" :size="34" class="findings__hero-icon text-green-500" />
									<div class="findings__hero-body">
										<span class="findings__hero-title">Looks good</span>
										<span class="findings__hero-text">
											No structural, lint, or Graylog-query issues. Reference integrity and
											per-tenant field checks come next.
										</span>
									</div>
								</div>

								<n-empty
									v-else-if="!result && !validating"
									description="Start typing to validate."
									class="findings__empty"
								/>

								<section v-for="g of findingGroups" v-else :key="g.level" class="finding-group">
									<h4 class="section-title">{{ g.label }} ({{ g.items.length }})</h4>
									<div class="finding-group__rows">
										<div
											v-for="(f, i) of g.items"
											:key="`${g.level}-${i}`"
											class="finding-row"
											:class="[`is-${g.level}`, { clickable: !!f.line }]"
											@click="jumpTo(f)"
										>
											<span class="finding-row__level">{{ g.level }}</span>
											<div class="finding-row__body">
												<div class="finding-row__meta">
													<code class="finding-row__code">{{ f.code }}</code>
													<span v-if="f.line">line {{ f.line }}</span>
													<span v-else-if="f.path">{{ f.path }}</span>
												</div>
												<span class="finding-row__msg">{{ f.message }}</span>
											</div>
											<Icon v-if="f.line" :name="JumpIcon" :size="14" class="finding-row__jump" />
										</div>
									</div>
								</section>
							</div>
						</n-scrollbar>
					</n-tab-pane>
					<n-tab-pane name="syntax" tab="Graylog syntax">
						<n-scrollbar trigger="none" class="h-full">
							<div class="syntax-pane">
								<GraylogSyntaxReference />
							</div>
						</n-scrollbar>
					</n-tab-pane>
				</n-tabs>
			</aside>
		</div>

		<BacktestModal v-model:show="showBacktest" :yaml="yamlText" />
		<PublishModal v-model:show="showPublish" :yaml="yamlText" :valid="!!result?.valid" />
	</div>
</template>

<script setup lang="ts">
import type { LintFinding, ValidateRuleResponse } from "@/types/copilot-searches"
import { useStorage, watchDebounced } from "@vueuse/core"
import { NButton, NButtonGroup, NEmpty, NScrollbar, NSpin, NTabPane, NTabs, NTag, NTooltip, useMessage } from "naive-ui"
import { computed, onMounted, ref } from "vue"
import { useRouter } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import BacktestModal from "@/components/copilotSearches/BacktestModal.vue"
import GraylogSyntaxReference from "@/components/copilotSearches/GraylogSyntaxReference.vue"
import PublishModal from "@/components/copilotSearches/PublishModal.vue"
import RuleYamlEditor from "@/components/copilotSearches/RuleYamlEditor.vue"
import { getApiErrorMessage } from "@/utils"

const EditorIcon = "carbon:code"
const YamlIcon = "carbon:document"
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

const yamlText = ref("")
const result = ref<ValidateRuleResponse | null>(null)
const validating = ref(false)
const rightTab = ref<"validation" | "syntax">("validation")
const showBacktest = ref(false)
const showPublish = ref(false)
const editorRef = ref<InstanceType<typeof RuleYamlEditor> | null>(null)

// Findings grouped by level, each sorted by line.
const byLine = (a: LintFinding, b: LintFinding) => (a.line ?? 1e9) - (b.line ?? 1e9)
const errorFindings = computed<LintFinding[]>(() =>
	(result.value?.findings || []).filter(f => f.level === "error").sort(byLine)
)
const warningFindings = computed<LintFinding[]>(() =>
	(result.value?.findings || []).filter(f => f.level === "warning").sort(byLine)
)

/** Both severity blocks in one list so the panel renders them from a single loop. */
const findingGroups = computed(() =>
	[
		{ level: "error" as const, label: "Errors", items: errorFindings.value },
		{ level: "warning" as const, label: "Warnings", items: warningFindings.value }
	].filter(g => g.items.length)
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
	return `${base}${enabled ? "" : '# Optional — only for threshold / aggregation rules (e.g. "N events per user in 10m").\n# Leave enabled: false (or delete this whole block) for a simple match rule.\n'}aggregation:
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

// Draft auto-save: never lose an in-progress rule to a refresh/navigation.
const draft = useStorage("copilot-searches:editor-draft", "", localStorage, {
	onError: () => {
		// storage full/blocked — drafts are best-effort
	}
})

watchDebounced(
	yamlText,
	() => {
		draft.value = yamlText.value || ""
	},
	{ debounce: 600 }
)

onMounted(() => {
	if (draft.value.trim()) {
		yamlText.value = draft.value
		message.info("Restored your draft — use the template buttons to start fresh.")
	} else {
		yamlText.value = makeTemplate("disabled")
	}
})
</script>

<style scoped lang="scss">
.editor-page {
	gap: 14px;
}

.editor-head {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 10px;

	h1 {
		font-size: 17px;
		font-weight: 600;
		line-height: 1.2;
		white-space: nowrap;
	}
}

.editor-head__title,
.editor-head__status {
	display: flex;
	align-items: center;
	gap: 8px;
}

/*
 * One box for the whole workspace, split like SegmentedPage: an authoring half and a
 * reference half, each with its own toolbar strip and a full-height content area.
 */
.workspace {
	--workspace-toolbar-height: 48px;

	display: flex;
	min-height: 0;
	flex-grow: 1;
	flex-direction: column;
	overflow: hidden;
	border: 1px solid var(--border-color);
	border-radius: var(--border-radius);
	background-color: var(--bg-default-color);

	@media (min-width: 1024px) {
		flex-direction: row;
	}
}

.workspace__pane {
	display: flex;
	min-width: 0;
	min-height: 0;
	flex: 1 1 0;
	flex-direction: column;
}

.workspace__pane--main {
	border-block-end: 1px solid var(--border-color);

	@media (min-width: 1024px) {
		border-block-end: none;
		border-inline-end: 1px solid var(--border-color);
	}
}

/* The reference side reads as a panel, not as more canvas — hence the recessed ground. */
.workspace__pane--aside {
	background-color: var(--bg-secondary-color);

	/*
	 * Stacked layout: the findings list claims only the height it needs — capped at 40% of the
	 * workspace — so the editor keeps the rest. The syntax reference is long-form reading and
	 * keeps its full half. Side by side, both halves are equal again.
	 */
	&.is-fit {
		max-height: 40%;
		flex: 0 1 auto;
	}

	@media (min-width: 1024px) {
		&.is-fit {
			max-height: none;
			flex: 1 1 0;
		}
	}
}

.workspace__toolbar {
	display: flex;
	height: var(--workspace-toolbar-height);
	min-height: var(--workspace-toolbar-height);
	align-items: center;
	gap: 10px;
	padding: 0 14px;
	border-block-end: 1px solid var(--border-color);
}

.toolbar__group {
	display: flex;
	min-width: 0;
	align-items: center;
	gap: 10px;
}

.toolbar__icon {
	flex-shrink: 0;
	color: var(--fg-secondary-color);
}

.toolbar__title {
	font-size: 13px;
	font-weight: 600;
	white-space: nowrap;
}

.toolbar__label {
	font-size: 10px;
	font-weight: 600;
	letter-spacing: 0.08em;
	text-transform: uppercase;
	white-space: nowrap;
	color: var(--fg-secondary-color);
}

.toolbar__hint {
	display: flex;
	align-items: center;
	cursor: help;
	color: var(--fg-secondary-color);
	opacity: 0.7;
	transition: opacity 0.15s var(--bezier-ease);

	&:hover {
		opacity: 1;
	}
}

.toolbar__divider {
	width: 1px;
	height: 16px;
	flex-shrink: 0;
	background-color: var(--border-color);
}

.workspace__content {
	display: flex;
	min-height: 0;
	flex-grow: 1;
	flex-direction: column;
	overflow: hidden;

	> * {
		min-height: 0;
		flex-grow: 1;
	}
}

/* The tab nav doubles as this pane's toolbar strip, so both halves line up. */
.aside-tabs {
	display: flex;
	min-height: 0;
	flex-grow: 1;
	flex-direction: column;

	:deep(.n-tabs-nav) {
		display: flex;
		height: var(--workspace-toolbar-height);
		min-height: var(--workspace-toolbar-height);
		align-items: center;
		padding: 0 14px;
		border-block-end: 1px solid var(--border-color);
	}

	:deep(.n-tabs-pane-wrapper) {
		display: flex;
		min-height: 0;
		flex-grow: 1;
		overflow: hidden;
	}

	:deep(.n-tab-pane) {
		display: flex;
		width: 100%;
		height: 100%;
		min-height: 0;
		flex-direction: column;
		padding: 0;
	}
}

.findings {
	display: flex;
	flex-direction: column;
	gap: 18px;
	padding: 14px;
}

.syntax-pane {
	padding: 14px;
}

/*
 * Stacked, the reference panel is a wide, short strip — so the placeholders lie down and stay
 * inside 100px instead of eating height the editor needs. Side by side they stand up again.
 */
.findings__hero {
	display: flex;
	max-height: 100px;
	align-items: center;
	justify-content: flex-start;
	gap: 12px;
	overflow: hidden;
	padding: 12px 14px;
	text-align: start;

	@media (min-width: 1024px) {
		max-height: none;
		flex-direction: column;
		justify-content: center;
		gap: 8px;
		padding: 52px 16px;
		text-align: center;
	}
}

.findings__hero-icon {
	flex-shrink: 0;
}

.findings__hero-body {
	display: flex;
	min-width: 0;
	flex-direction: column;
	gap: 2px;

	@media (min-width: 1024px) {
		align-items: center;
		gap: 8px;
	}
}

.findings__empty {
	max-height: 100px;
	overflow: hidden;
	padding: 12px 14px;

	@media (min-width: 1024px) {
		max-height: none;
		padding: 52px 16px;
	}
}

.findings__hero-title {
	font-size: 14px;
	font-weight: 600;

	@media (min-width: 1024px) {
		font-size: 15px;
	}
}

.findings__hero-text {
	display: -webkit-box;
	overflow: hidden;
	font-size: 12px;
	line-height: 1.45;
	color: var(--fg-secondary-color);
	-webkit-box-orient: vertical;
	-webkit-line-clamp: 2;

	@media (min-width: 1024px) {
		display: block;
		max-width: 22rem;
		font-size: 13px;
		line-height: 1.5;
		-webkit-line-clamp: none;
	}
}

.finding-group {
	display: flex;
	flex-direction: column;
	gap: 8px;
}

.finding-group__rows {
	display: flex;
	flex-direction: column;
	gap: 6px;
}

.finding-row {
	--accent: var(--border-color);

	position: relative;
	display: flex;
	align-items: flex-start;
	gap: 10px;
	overflow: hidden;
	padding: 10px 12px 10px 14px;
	border: 1px solid var(--border-color);
	border-radius: var(--border-radius-small);
	/* lifted off the recessed panel ground */
	background-color: var(--bg-default-color);
	transition:
		background-color 0.15s var(--bezier-ease),
		border-color 0.15s var(--bezier-ease);

	&::before {
		content: "";
		position: absolute;
		inset: 0 auto 0 0;
		width: 3px;
		background-color: var(--accent);
	}

	&.is-error {
		--accent: var(--error-color);
	}

	&.is-warning {
		--accent: var(--warning-color);
	}

	&.clickable {
		cursor: pointer;

		&:hover {
			border-color: var(--accent);
			background-color: var(--hover-005-color);
		}
	}
}

.finding-row__level {
	min-width: 52px;
	flex-shrink: 0;
	padding-top: 2px;
	font-family: var(--font-family-mono);
	font-size: 10px;
	font-weight: 600;
	letter-spacing: 0.08em;
	text-transform: uppercase;
	color: var(--accent);
}

.finding-row__body {
	display: flex;
	min-width: 0;
	flex-grow: 1;
	flex-direction: column;
	gap: 3px;
}

.finding-row__meta {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 8px;
	font-family: var(--font-family-mono);
	font-size: 11px;
	color: var(--fg-secondary-color);
}

/* Neutralise the global `code` pill — inside a row the code reads as plain mono text. */
.finding-row__code {
	padding: 0;
	background: none;
	font-size: 11px;
	color: var(--fg-default-color);
}

.finding-row__msg {
	font-size: 13px;
	line-height: 1.45;
	overflow-wrap: anywhere;
}

.finding-row__jump {
	margin-top: 2px;
	flex-shrink: 0;
	color: var(--fg-secondary-color);
	opacity: 0.6;
}

.section-title {
	font-size: 11px;
	font-weight: 600;
	letter-spacing: 0.06em;
	text-transform: uppercase;
	color: var(--fg-secondary-color);
}
</style>
