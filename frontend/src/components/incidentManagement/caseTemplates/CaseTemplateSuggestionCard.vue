<template>
	<CardEntity size="small" hoverable :highlighted="selected" card-entity-class="h-full" main-box-class="grow">
		<template #headerMain>
			<div class="flex items-center gap-2">
				<div class="text-default text-base leading-snug font-semibold text-balance">
					{{ suggestion.template.name }}
				</div>
				<n-tag v-if="suggestion.template.is_default" size="tiny" :bordered="false">default</n-tag>
			</div>
		</template>

		<template #headerExtra>
			<div class="flex items-center gap-2">
				<!--
					Why this card is at the top. A fired auto-apply condition
					sorts ahead of everything regardless of score, so the reason
					for the ordering has to be visible at a glance — otherwise a
					lower-scoring card sitting first looks like a bug.
				-->
				<Badge v-if="suggestion.condition_matched" color="success" type="splitted" bright size="small">
					<template #iconLeft>
						<Icon :name="SIGNAL_ICONS.condition" :size="13" />
					</template>
					<template #label>Auto-apply</template>
					<template #value>fires</template>
				</Badge>
				<Badge type="splitted" size="small" :color="confidenceColor" bright>
					<template #label>Match</template>
					<template #value>{{ confidenceLabel }}</template>
				</Badge>
			</div>
		</template>

		<template #default>
			<div class="flex flex-col gap-3">
				<p v-if="suggestion.template.description" class="text-secondary line-clamp-2 text-sm">
					{{ suggestion.template.description }}
				</p>

				<!--
					The reasons ARE the ranking's explanation — a list an analyst
					cannot audit is a list they will not trust. Rendered in the
					order the backend sent them (highest-scoring signal first).
				-->
				<div v-if="suggestion.reasons.length" class="flex flex-wrap items-center gap-1.5">
					<n-tag
						v-for="reason of suggestion.reasons"
						:key="`${reason.signal}-${reason.detail}`"
						size="small"
						:bordered="false"
						:type="reasonTagType(reason)"
						:title="reason.points ? `${reason.detail} (+${reason.points})` : reason.detail"
					>
						<template #icon>
							<Icon :name="reasonIcon(reason.signal)" :size="13" />
						</template>
						{{ reason.detail }}
					</n-tag>
				</div>

				<!--
					Task preview. The full task list already arrived with the
					suggestion, so expanding costs no request — which is why this
					is a plain toggle and not a lazy fetch.
				-->
				<div v-if="suggestion.template.tasks.length" class="flex flex-col gap-2">
					<n-button text size="tiny" class="self-start" @click="expanded = !expanded">
						<template #icon>
							<Icon :name="expanded ? CollapseIcon : ExpandIcon" :size="14" />
						</template>
						{{ expanded ? "Hide" : "Preview" }} {{ suggestion.template.tasks.length }} task{{
							suggestion.template.tasks.length === 1 ? "" : "s"
						}}
					</n-button>

					<n-collapse-transition :show="expanded">
						<ol class="text-secondary flex flex-col gap-1 pl-4 text-sm">
							<li v-for="task of suggestion.template.tasks" :key="task.id" class="list-decimal">
								<span>{{ task.title }}</span>
								<n-tag v-if="task.mandatory" size="tiny" :bordered="false" type="warning" class="ml-2">
									mandatory
								</n-tag>
							</li>
						</ol>
					</n-collapse-transition>
				</div>
				<p v-else class="text-tertiary text-sm italic">This template has no tasks yet.</p>
			</div>
		</template>

		<template #footerMain>
			<div class="flex h-full flex-wrap items-center gap-2">
				<Badge type="splitted" size="small">
					<template #iconLeft>
						<Icon :name="TasksIcon" :size="13" />
					</template>
					<template #label>Tasks</template>
					<template #value>{{ suggestion.template.tasks.length }}</template>
				</Badge>
				<Badge v-if="mandatoryCount > 0" color="warning" type="splitted" bright size="small">
					<template #label>Mandatory</template>
					<template #value>{{ mandatoryCount }}</template>
				</Badge>
				<Badge v-if="scopeLabel" type="splitted" size="small">
					<template #label>Scope</template>
					<template #value>{{ scopeLabel }}</template>
				</Badge>
			</div>
		</template>

		<template #footerExtra>
			<div class="flex flex-wrap items-center justify-end gap-2">
				<n-button
					size="tiny"
					:type="selected ? 'success' : 'primary'"
					:secondary="!selected"
					:loading="applying"
					@click="emit('select', suggestion)"
				>
					<template #icon>
						<Icon :name="selected ? SelectedIcon : ApplyIcon" />
					</template>
					{{ selected ? "Selected" : applyLabel || "Use this template" }}
				</n-button>
			</div>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type {
	CaseTemplateSuggestion,
	SuggestionReason,
	SuggestionSignal
} from "@/types/incidentManagement/case-templates"
import { NButton, NCollapseTransition, NTag } from "naive-ui"
import { computed, ref } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"

const { suggestion, selected, applying, applyLabel } = defineProps<{
	suggestion: CaseTemplateSuggestion
	selected?: boolean
	applying?: boolean
	/** Overrides the CTA text — "Use this template" when creating, "Apply" when the case exists. */
	applyLabel?: string
}>()

const emit = defineEmits<{
	(e: "select", value: CaseTemplateSuggestion): void
}>()

const TasksIcon = "carbon:task"
const ApplyIcon = "carbon:play-filled-alt"
const SelectedIcon = "carbon:checkmark-filled"
const ExpandIcon = "carbon:chevron-down"
const CollapseIcon = "carbon:chevron-up"

// Only `carbon:`, `mdi:` and `logos:` collections are bundled — anything else
// renders as an empty box with no console error.
const SIGNAL_ICONS: Record<SuggestionSignal, string> = {
	condition: "carbon:filter",
	condition_unverified: "carbon:warning-alt",
	customer: "carbon:enterprise",
	source: "carbon:data-base",
	tag: "carbon:tag",
	mitre: "carbon:security",
	mitre_parent: "carbon:security",
	mitre_name: "carbon:security",
	rule_group: "carbon:rule",
	keyword: "carbon:search",
	usage: "carbon:chart-line",
	default: "carbon:star"
}

const expanded = ref(false)

const mandatoryCount = computed(() => suggestion.template.tasks.filter(t => t.mandatory).length)

const confidenceColor = computed(() => {
	if (suggestion.confidence === "high") return "success"
	if (suggestion.confidence === "medium") return "primary"
	return undefined
})

const confidenceLabel = computed(() => {
	if (suggestion.confidence === "high") return "Strong"
	if (suggestion.confidence === "medium") return "Likely"
	return "Possible"
})

/**
 * "Global / any source" is worth stating explicitly — an analyst comparing two
 * suggestions needs to see that one is pinned to their customer and the other
 * is the catch-all.
 */
const scopeLabel = computed(() => {
	const parts = [suggestion.template.customer_code, suggestion.template.source].filter(Boolean)
	return parts.length ? parts.join(" — ") : "global"
})

function reasonIcon(signal: SuggestionSignal): string {
	return SIGNAL_ICONS[signal] ?? "carbon:information"
}

/**
 * `condition_unverified` is the one reason that is a caveat rather than a
 * credit — it scores nothing and warns that the originating event could not be
 * read, so it must not look like the others.
 */
function reasonTagType(reason: SuggestionReason): "warning" | "success" | "default" {
	if (reason.signal === "condition_unverified") return "warning"
	if (reason.signal === "condition") return "success"
	return "default"
}
</script>
