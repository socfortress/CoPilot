<template>
	<div v-if="!ruleIds.length" class="preview-empty text-secondary text-xs">No rules</div>
	<div v-else class="preview-wrap flex flex-col gap-1">
		<div class="text-tertiary text-xs tracking-wide uppercase">
			{{ headerLabel }}
		</div>

		<div
			v-for="id in shownIds"
			:key="id"
			class="preview-row flex flex-col gap-1"
			title="Click to open rule details"
			@click="onRowClick($event, id)"
		>
			<div class="flex items-center gap-2">
				<Icon :name="platformIconFor(index[id]?.platform)" :size="14" class="preview-platform shrink-0" />
				<span class="preview-name text-default text-xs">{{ index[id]?.name || id }}</span>
				<span
					v-if="index[id]?.severity"
					class="preview-sev text-xs"
					:class="`preview-sev-${index[id]!.severity.toLowerCase()}`"
				>
					{{ index[id]!.severity }}
				</span>
			</div>

			<div v-if="index[id]?.data_sources?.length" class="preview-sources flex flex-wrap items-center gap-1">
				<span v-for="source in index[id]!.data_sources" :key="source" class="preview-source text-xs">
					{{ source }}
				</span>
			</div>
		</div>

		<div v-if="remainder > 0" class="text-tertiary text-xs">+ {{ remainder }} more — click cell to view all</div>
	</div>
</template>

<script setup lang="ts">
// TODO-FE: refactor
import type { MitreRuleIndexEntry } from "@/types/copilotSearches.d"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"

const props = defineProps<{
	ruleIds: string[]
	index: Record<string, MitreRuleIndexEntry>
	extraViaSubs?: number
}>()

const emit = defineEmits<{
	(e: "open-rule", ruleId: string): void
}>()

const PREVIEW_LIMIT = 6

const platformIcons: Record<string, string> = {
	linux: "proicons:linux",
	windows: "mdi:microsoft",
	powershell: "codicon:terminal-powershell",
	cve: "carbon:security",
	unknown: "carbon:help"
}

const shownIds = computed(() => props.ruleIds.slice(0, PREVIEW_LIMIT))
const remainder = computed(() => props.ruleIds.length - shownIds.value.length)

const headerLabel = computed(() => {
	const countLabel = `${props.ruleIds.length} rule${props.ruleIds.length === 1 ? "" : "s"}`
	if (!props.extraViaSubs) return countLabel
	return `${countLabel} · +${props.extraViaSubs} via sub-techniques`
})

function platformIconFor(platform?: string) {
	const key = (platform || "unknown").toLowerCase()
	return platformIcons[key] || platformIcons.unknown
}

function onRowClick(event: MouseEvent, ruleId: string) {
	event.stopPropagation()
	emit("open-rule", ruleId)
}
</script>

<style scoped lang="scss">
.preview-wrap {
	max-width: 360px;
}
.preview-row {
	cursor: pointer;
	padding: 2px 4px;
	border-radius: 3px;
	transition: background-color 0.1s;
}
.preview-row:hover {
	background: rgba(var(--primary-color-rgb) / 0.1);
}
.preview-row:hover .preview-name {
	color: var(--primary-color);
}
.preview-row .preview-name {
	flex: 1;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}
.preview-platform {
	opacity: 0.85;
}
.preview-sources {
	margin-left: 22px;
}
.preview-source {
	font-size: 0.6rem;
	font-weight: 500;
	letter-spacing: 0.02em;
	color: var(--fg-tertiary-color);
	background: var(--bg-default-color);
	border: 1px solid var(--border-color);
	border-radius: 3px;
	padding: 1px 5px;
}
.preview-sev {
	font-size: 0.65rem;
	font-weight: 600;
	text-transform: uppercase;
	padding: 1px 6px;
	border-radius: 3px;
	border: 1px solid var(--border-color);
	color: var(--fg-secondary-color);
}
.preview-sev-low {
	color: var(--info-color);
	border-color: rgba(var(--info-color-rgb) / 0.4);
	background: rgba(var(--info-color-rgb) / 0.1);
}
.preview-sev-medium {
	color: var(--warning-color);
	border-color: rgba(var(--warning-color-rgb) / 0.4);
	background: rgba(var(--warning-color-rgb) / 0.1);
}
.preview-sev-high {
	color: var(--error-color);
	border-color: rgba(var(--error-color-rgb) / 0.4);
	background: rgba(var(--error-color-rgb) / 0.1);
}
.preview-sev-critical {
	color: var(--error-color);
	border-color: var(--error-color);
	background: rgba(var(--error-color-rgb) / 0.18);
}
</style>
