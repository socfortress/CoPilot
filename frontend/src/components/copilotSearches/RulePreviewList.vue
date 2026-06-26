<template>
	<div v-if="!ruleIds.length" class="text-tertiary px-1 py-2 text-xs">No rules</div>

	<div v-else class="flex max-w-90 flex-col gap-2">
		<header class="border-default flex flex-col gap-0.5 border-b pb-2">
			<span class="text-tertiary text-3xs font-medium tracking-wider uppercase">Rules</span>
			<span class="text-default font-mono text-xs leading-none">{{ headerCount }}</span>
			<span v-if="extraViaSubs" class="text-tertiary text-3xs font-mono">
				+{{ extraViaSubs }} via sub-techniques
			</span>
		</header>

		<ul class="m-0 flex list-none flex-col gap-1 p-0">
			<li v-for="id in shownIds" :key="id">
				<button
					type="button"
					class="border-default bg-secondary/50 hover:border-primary/55 hover:bg-primary/10 group w-full cursor-pointer rounded-md border px-2 py-1.5 text-left transition-colors"
					:title="rowTitle(id)"
					@click="onRowClick($event, id)"
				>
					<div class="flex min-w-0 items-center gap-2">
						<PlatformIcon
							:platform="entryFor(id)?.platform ?? 'unknown'"
							:size="14"
							class="text-secondary shrink-0 opacity-90"
						/>
						<span class="text-default group-hover:text-primary min-w-0 flex-1 truncate text-xs font-medium">
							{{ entryFor(id)?.name || id }}
						</span>
						<n-tag
							v-if="entryFor(id)?.severity"
							size="tiny"
							:bordered="false"
							:type="severityTagType(entryFor(id)!.severity)"
							class="text-3xs! shrink-0 font-mono uppercase"
						>
							{{ entryFor(id)!.severity }}
						</n-tag>
					</div>

					<div v-if="entryFor(id)?.data_sources?.length" class="mt-1.5 flex flex-wrap gap-1 pl-6">
						<span
							v-for="source in entryFor(id)!.data_sources"
							:key="source"
							class="text-tertiary border-default bg-default text-3xs rounded-sm border px-1.5 py-px font-mono tracking-wide uppercase"
						>
							{{ source }}
						</span>
					</div>
				</button>
			</li>
		</ul>

		<p v-if="remainder > 0" class="text-tertiary text-3xs leading-snug">
			+{{ remainder }} more · click sub-technique cell for full list
		</p>
	</div>
</template>

<script setup lang="ts">
import type { MitreRuleIndexEntry } from "@/types/copilot-searches"
import { NTag } from "naive-ui"
import { computed } from "vue"
import PlatformIcon from "@/components/common/PlatformIcon.vue"

const props = defineProps<{
	ruleIds: string[]
	index: Record<string, MitreRuleIndexEntry>
	extraViaSubs?: number
}>()

const emit = defineEmits<{
	(e: "open-rule", ruleId: string): void
}>()

const PREVIEW_LIMIT = 6

const shownIds = computed(() => props.ruleIds.slice(0, PREVIEW_LIMIT))
const remainder = computed(() => props.ruleIds.length - shownIds.value.length)

const headerCount = computed(() => {
	const n = props.ruleIds.length
	return `${n} rule${n === 1 ? "" : "s"}`
})

function entryFor(id: string) {
	return props.index[id]
}

function severityTagType(severity: string): "default" | "error" | "info" | "success" | "warning" {
	switch (severity.toLowerCase()) {
		case "low":
			return "info"
		case "medium":
			return "warning"
		case "high":
		case "critical":
			return "error"
		default:
			return "default"
	}
}

function rowTitle(id: string) {
	const name = entryFor(id)?.name || id
	return `Open ${name}`
}

function onRowClick(event: MouseEvent, ruleId: string) {
	event.stopPropagation()
	emit("open-rule", ruleId)
}
</script>
