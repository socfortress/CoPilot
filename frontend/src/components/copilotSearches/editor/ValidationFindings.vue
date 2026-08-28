<template>
	<div class="flex flex-col gap-4.5 p-3.5">
		<!-- clean bill of health -->
		<div
			v-if="result?.valid && !result.warning_count"
			class="flex max-h-25 items-center justify-start gap-3 overflow-hidden p-3 text-start lg:max-h-none lg:flex-col lg:justify-center lg:gap-2 lg:p-13 lg:text-center"
		>
			<Icon :name="OkIcon" :size="34" class="shrink-0 text-green-500" />
			<div class="flex min-w-0 flex-col gap-0.5 lg:items-center lg:gap-2">
				<span class="text-sm font-semibold lg:text-[15px]">Looks good</span>
				<span
					class="text-secondary line-clamp-2 text-xs leading-snug lg:line-clamp-none lg:max-w-88 lg:text-[13px] lg:leading-normal"
				>
					No structural, lint, or Graylog-query issues. Reference integrity and per-tenant field checks come
					next.
				</span>
			</div>
		</div>

		<n-empty
			v-else-if="!result && !validating"
			description="Start typing to validate."
			class="max-h-25 overflow-hidden p-3 lg:max-h-none lg:p-13"
		/>

		<section v-for="group of findingGroups" v-else :key="group.level" class="flex flex-col gap-2">
			<SectionHeading>{{ group.label }} ({{ group.items.length }})</SectionHeading>
			<div class="flex flex-col gap-1.5">
				<div
					v-for="(finding, i) of group.items"
					:key="`${group.level}-${i}`"
					class="border-default relative flex items-start gap-2.5 overflow-hidden rounded-md border py-2.5 pr-3 pl-3.5 transition-colors before:absolute before:inset-y-0 before:left-0 before:w-[3px] before:bg-(--accent)"
					:class="[
						group.level === 'error' ? '[--accent:var(--error-color)]' : '[--accent:var(--warning-color)]',
						finding.line ? 'hover:bg-hover-005 cursor-pointer hover:border-(--accent)' : ''
					]"
					@click="emit('jump', finding)"
				>
					<span class="text-3xs w-13 shrink-0 pt-0.5 font-mono font-semibold tracking-widest text-(--accent) uppercase">
						{{ group.level }}
					</span>
					<div class="flex min-w-0 grow flex-col gap-0.75">
						<div class="text-secondary text-2xs flex flex-wrap items-center gap-2 font-mono">
							<code class="text-default text-2xs bg-transparent p-0">{{ finding.code }}</code>
							<span v-if="finding.line">line {{ finding.line }}</span>
							<span v-else-if="finding.path">{{ finding.path }}</span>
						</div>
						<span class="text-[13px] leading-snug [overflow-wrap:anywhere]">{{ finding.message }}</span>
					</div>
					<Icon
						v-if="finding.line"
						:name="JumpIcon"
						:size="14"
						class="text-secondary mt-0.5 shrink-0 opacity-60"
					/>
				</div>
			</div>
		</section>
	</div>
</template>

<script setup lang="ts">
import type { LintFinding, ValidateRuleResponse } from "@/types/copilot-searches"
import { NEmpty } from "naive-ui"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"
import SectionHeading from "@/components/copilotSearches/SectionHeading.vue"

const { result = null, validating = false } = defineProps<{
	result?: ValidateRuleResponse | null
	validating?: boolean
}>()

const emit = defineEmits<{
	(e: "jump", finding: LintFinding): void
}>()

const OkIcon = "carbon:checkmark-filled"
const JumpIcon = "carbon:arrow-right"

/** Findings by severity, each sorted by line, empty levels dropped. */
const findingGroups = computed(() => {
	const byLine = (a: LintFinding, b: LintFinding) => (a.line ?? Number.MAX_SAFE_INTEGER) - (b.line ?? Number.MAX_SAFE_INTEGER)
	const findings = result?.findings || []

	return [
		{ level: "error" as const, label: "Errors", items: findings.filter(f => f.level === "error").sort(byLine) },
		{ level: "warning" as const, label: "Warnings", items: findings.filter(f => f.level === "warning").sort(byLine) }
	].filter(group => group.items.length)
})
</script>
