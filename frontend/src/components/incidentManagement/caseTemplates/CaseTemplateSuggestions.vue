<template>
	<div class="case-template-suggestions flex flex-col gap-3">
		<div class="flex flex-wrap items-center justify-between gap-2">
			<div class="flex items-center gap-2">
				<Icon :name="SuggestIcon" :size="16" />
				<span class="text-default text-sm font-semibold">Suggested templates</span>
				<n-tag v-if="totalCandidates > suggestions.length" size="tiny" :bordered="false">
					top {{ suggestions.length }} of {{ totalCandidates }}
				</n-tag>
			</div>

			<div class="flex items-center gap-2">
				<slot name="browseAll" />
			</div>
		</div>

		<n-spin :show="loading" content-class="flex flex-col gap-3">
			<template v-if="suggestions.length">
				<div class="flex flex-col gap-3">
					<CaseTemplateSuggestionCard
						v-for="suggestion of suggestions"
						:key="suggestion.template.id"
						:suggestion
						:apply-label
						:selected="selectedId === suggestion.template.id"
						:applying="applyingId === suggestion.template.id"
						@select="toggleSelection(suggestion)"
					/>
				</div>
			</template>

			<!--
				Two distinct empty states. "Nothing ranked" is normal on a fresh
				deployment with no templates yet; a failed lookup is not, and
				saying so lets the analyst know the full template list is still
				trustworthy even though the ranking isn't there. Worded without
				reference to creating a case — this panel is also used when
				applying a template to one that already exists.
			-->
			<n-alert v-else-if="failed && !loading" type="warning" :bordered="false" size="small">
				Couldn't rank templates for this context. Choose one manually instead — nothing else is affected.
			</n-alert>
			<n-empty v-else-if="!loading" description="No templates match this context yet" class="justify-center py-6">
				<template #extra>
					<span class="text-tertiary text-xs">
						Suggestions improve as templates gain tasks mentioning the techniques and tags they cover.
					</span>
				</template>
			</n-empty>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { CaseTemplateSuggestQuery } from "@/api/endpoints/incidentManagement/case-templates"
import type { ApiError } from "@/types/common"
import type { CaseTemplate, CaseTemplateSuggestion } from "@/types/incidentManagement/case-templates"
import { NAlert, NEmpty, NSpin, NTag } from "naive-ui"
import { ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import CaseTemplateSuggestionCard from "./CaseTemplateSuggestionCard.vue"

const { alertId, customerCode, source, limit, selectedTemplateId, applyingId, applyLabel } = defineProps<{
	/** Creating from an alert — enables full contextual scoring. */
	alertId?: number | null
	/** Manual creation. Ignored by the backend when alertId is set. */
	customerCode?: string | null
	source?: string | null
	limit?: number
	/** Reflects the parent's current choice so the panel and any template dropdown agree. */
	selectedTemplateId?: number | null
	applyingId?: number | null
	applyLabel?: string
}>()

const emit = defineEmits<{
	/** null when the analyst clears their choice. */
	(e: "select", value: CaseTemplate | null): void
	(e: "loaded", value: CaseTemplateSuggestion[]): void
}>()

const SuggestIcon = "carbon:idea"

const suggestions = ref<CaseTemplateSuggestion[]>([])
const totalCandidates = ref(0)
const loading = ref(false)
const failed = ref(false)
const selectedId = ref<number | null>(selectedTemplateId ?? null)

// Sequence guard: customer_code changes fire this repeatedly while the analyst
// tabs through the form, and axios gives no ordering guarantee. Without it a
// slow early response can overwrite a fast later one and the panel ends up
// showing suggestions for the previous customer.
let requestToken = 0

function toggleSelection(suggestion: CaseTemplateSuggestion) {
	if (selectedId.value === suggestion.template.id) {
		clearSelection()
		return
	}
	selectedId.value = suggestion.template.id
	emit("select", suggestion.template)
}

function clearSelection() {
	selectedId.value = null
	emit("select", null)
}

function load() {
	// Nothing to score against: no alert and no customer. Show the empty state
	// rather than firing a request that can only come back empty.
	if (!alertId && !customerCode && !source) {
		suggestions.value = []
		totalCandidates.value = 0
		failed.value = false
		return
	}

	const token = ++requestToken
	loading.value = true
	failed.value = false

	const query: CaseTemplateSuggestQuery = { limit: limit ?? 5 }
	if (alertId) {
		query.alertId = alertId
	} else {
		query.customerCode = customerCode ?? null
		query.source = source ?? null
	}

	Api.incidentManagement.caseTemplates
		.suggestTemplates(query)
		.then(res => {
			if (token !== requestToken) return
			if (res.data.success) {
				suggestions.value = res.data.suggestions || []
				totalCandidates.value = res.data.total_candidates || 0
				emit("loaded", suggestions.value)
			} else {
				failed.value = true
				suggestions.value = []
				totalCandidates.value = 0
			}
		})
		.catch((err: ApiError) => {
			if (token !== requestToken) return
			// Deliberately not a toast. This panel sits beside a form the
			// analyst can still submit; an error popup would imply the whole
			// action failed when only the ranking did.
			console.warn("Failed to load case template suggestions:", err)
			failed.value = true
			suggestions.value = []
			totalCandidates.value = 0
		})
		.finally(() => {
			if (token === requestToken) loading.value = false
		})
}

// Keep in step with a selection made outside the panel (e.g. the template
// dropdown on the create-case form).
watch(
	() => selectedTemplateId,
	value => {
		selectedId.value = value ?? null
	}
)

watch(
	() => [alertId, customerCode, source, limit],
	() => load(),
	{ immediate: true }
)

defineExpose({ load })
</script>
