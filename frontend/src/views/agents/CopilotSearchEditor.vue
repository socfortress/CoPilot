<template>
	<div class="page page-wrapped page-without-footer flex flex-col gap-3.5">
		<!-- Page header — identity, live validation status, rule-level actions -->
		<header class="flex flex-wrap items-center gap-2.5">
			<n-button quaternary circle size="small" title="Back to searches" @click="goBack">
				<template #icon><Icon :name="BackIcon" :size="18" /></template>
			</n-button>

			<div class="flex items-center gap-2">
				<Icon :name="EditorIcon" :size="20" />
				<h1 class="text-[17px] leading-tight font-semibold whitespace-nowrap">Detection Rule Editor</h1>
				<n-tag size="small" round :bordered="false" type="info">Graylog-only</n-tag>
			</div>

			<div class="flex items-center gap-2">
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

		<!--
			Workspace — one box split like SegmentedPage: an authoring half and a reference
			half, each with its own toolbar strip over a full-height content area.
		-->
		<div class="border-default bg-default flex min-h-0 grow flex-col overflow-hidden rounded-lg border lg:flex-row">
			<!-- Authoring side -->
			<section class="border-default flex min-h-0 min-w-0 flex-1 flex-col border-b lg:border-e lg:border-b-0">
				<div class="border-default @container flex h-12 min-h-12 items-center gap-2.5 border-b px-3.5">
					<div class="flex min-w-0 items-center gap-2.5">
						<Icon :name="YamlIcon" :size="15" class="text-secondary shrink-0" />
						<span class="text-[13px] leading-none font-semibold whitespace-nowrap">Rule YAML</span>
						<n-tooltip>
							<template #trigger>
								<span class="text-secondary flex cursor-help items-center opacity-70 hover:opacity-100">
									<Icon :name="LockIcon" :size="13" />
								</span>
							</template>
							Required schema fields are locked — edit their values, not the keys
						</n-tooltip>
					</div>

					<!-- Kept as one group so a narrow pane wraps all three actions together. -->
					<div class="ms-auto flex items-center gap-2.5">
						<span
							class="text-secondary text-3xs leading-none font-semibold tracking-[0.08em] whitespace-nowrap uppercase"
						>
							Template
						</span>
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

						<span class="bg-border h-4 w-px shrink-0" />

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

				<div class="flex min-h-0 grow flex-col overflow-hidden [&>*]:min-h-0 [&>*]:grow">
					<RuleYamlEditor ref="editorRef" v-model:code="yamlText" @blocked="onBlocked" />
				</div>
			</section>

			<!--
				Reference side. Stacked, the findings list claims only the height it needs —
				capped at 40% — so the editor keeps the rest; the syntax reference is long-form
				reading and keeps its full half. Side by side, both halves are equal again.
			-->
			<aside
				class="bg-secondary flex min-h-0 min-w-0 flex-col lg:max-h-none lg:flex-1"
				:class="rightTab === 'validation' ? 'max-h-[40%] flex-none lg:flex-1' : 'flex-1'"
			>
				<n-tabs
					v-model:value="rightTab"
					type="segment"
					size="small"
					class="[&_.n-tabs-nav]:border-default flex min-h-0 grow flex-col [&_.n-tab-pane]:flex [&_.n-tab-pane]:h-full [&_.n-tab-pane]:min-h-0 [&_.n-tab-pane]:w-full [&_.n-tab-pane]:flex-col [&_.n-tab-pane]:p-0 [&_.n-tabs-nav]:flex [&_.n-tabs-nav]:h-12 [&_.n-tabs-nav]:min-h-12 [&_.n-tabs-nav]:items-center [&_.n-tabs-nav]:border-b [&_.n-tabs-nav]:px-3.5 [&_.n-tabs-pane-wrapper]:flex [&_.n-tabs-pane-wrapper]:min-h-0 [&_.n-tabs-pane-wrapper]:grow [&_.n-tabs-pane-wrapper]:overflow-hidden"
				>
					<n-tab-pane name="validation" tab="Validation">
						<n-scrollbar trigger="none" class="h-full">
							<ValidationFindings :result :validating @jump="jumpTo" />
						</n-scrollbar>
					</n-tab-pane>
					<n-tab-pane name="syntax" tab="Graylog syntax">
						<n-scrollbar trigger="none" class="h-full">
							<div class="p-3.5"><GraylogSyntaxReference /></div>
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
import type { TemplateKind } from "@/components/copilotSearches/editor/rule-templates"
import type { LintFinding, ValidateRuleResponse } from "@/types/copilot-searches"
import { useClipboard, useStorage, watchDebounced } from "@vueuse/core"
import { NButton, NButtonGroup, NScrollbar, NSpin, NTabPane, NTabs, NTag, NTooltip, useMessage } from "naive-ui"
import { onMounted, ref } from "vue"
import { useRouter } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import BacktestModal from "@/components/copilotSearches/BacktestModal.vue"
import { makeTemplate } from "@/components/copilotSearches/editor/rule-templates"
import ValidationFindings from "@/components/copilotSearches/editor/ValidationFindings.vue"
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

const message = useMessage()
const router = useRouter()
const { copy: copyToClipboard, isSupported: isClipboardSupported } = useClipboard()

const yamlText = ref("")
const result = ref<ValidateRuleResponse | null>(null)
const validating = ref(false)
const rightTab = ref<"validation" | "syntax">("validation")
const showBacktest = ref(false)
const showPublish = ref(false)
const editorRef = ref<InstanceType<typeof RuleYamlEditor> | null>(null)

function goBack() {
	router.push({ name: "CopilotSearches" })
}

function onBlocked(key: string) {
	message.warning(`"${key}" is a required field and can't be removed — edit its value instead.`)
}

function jumpTo(finding: LintFinding) {
	if (finding.line) editorRef.value?.goToLine(finding.line)
}

async function copyYaml() {
	if (!yamlText.value.trim()) return
	if (!isClipboardSupported.value) {
		message.error("Couldn't copy to clipboard")
		return
	}
	await copyToClipboard(yamlText.value)
	message.success("Rule YAML copied to clipboard")
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
