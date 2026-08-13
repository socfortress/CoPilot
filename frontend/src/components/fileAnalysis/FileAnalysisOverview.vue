<template>
	<div v-if="result" class="border-default flex flex-col gap-4 rounded-lg border p-4">
		<!-- Verdict + type headline -->
		<div class="flex flex-wrap items-center gap-3">
			<div class="flex items-center gap-2">
				<Icon :name="verdictIcon" :size="22" :class="reputationPending ? 'text-secondary' : verdictColorClass" />
				<span class="text-lg font-semibold capitalize">{{ verdict }}</span>
				<n-tag v-if="reputationPending" size="small" round :bordered="false" type="warning">
					<template #icon><Icon :name="ClockIcon" :size="12" /></template>
					static only · VirusTotal pending
				</n-tag>
			</div>
			<n-divider vertical />
			<span class="text-secondary text-sm">{{ prettyType }}</span>
			<div class="grow" />
			<n-tag v-if="hardened === false" type="warning" size="small" round :bordered="false">dev / unhardened</n-tag>
			<n-tag v-else type="success" size="small" round :bordered="false">
				<template #icon><Icon :name="ShieldIcon" :size="12" /></template>
				isolated
			</n-tag>
		</div>

		<!-- Why this verdict — makes tier disagreement visible instead of a bare label -->
		<div v-if="verdictReason" class="text-secondary flex items-start gap-2 text-xs">
			<Icon :name="ReasonIcon" :size="14" class="mt-0.5 shrink-0" />
			<span>{{ verdictReason }}</span>
		</div>

		<!-- Fact grid -->
		<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
			<div v-for="f in facts" :key="f.label" class="bg-secondary flex flex-col gap-1 rounded-lg p-3">
				<span class="text-secondary text-xs">{{ f.label }}</span>
				<span class="text-sm font-medium break-all">{{ f.value }}</span>
			</div>
		</div>

		<!-- Notable flags -->
		<div v-if="result.flags?.length" class="flex flex-wrap items-center gap-2">
			<span class="text-secondary text-xs">Signals:</span>
			<n-tag
				v-for="flag of result.flags"
				:key="flag"
				:type="flag === 'analysis_incomplete' ? 'default' : 'warning'"
				size="small"
				round
				:bordered="false"
			>
				{{ flag.replaceAll("_", " ") }}
			</n-tag>
		</div>

		<!-- Hashes (copyable) -->
		<div class="flex flex-col gap-1">
			<div v-for="h in hashes" :key="h.label" class="flex items-center gap-2 text-xs">
				<span class="text-secondary w-16 shrink-0">{{ h.label }}</span>
				<code class="grow break-all">{{ h.value }}</code>
				<n-button text size="tiny" @click="copy(h.value)">
					<template #icon><Icon :name="CopyIcon" :size="14" /></template>
				</n-button>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { FileAnalysisJob, FileAnalysisVerdict, InspectorResult } from "@/types/file-analysis"
import { NButton, NDivider, NTag, useMessage } from "naive-ui"
import { computed } from "vue"
import Icon from "@/components/common/Icon.vue"

const props = defineProps<{
	result?: InspectorResult | null
	job?: FileAnalysisJob | null
	reputationPending?: boolean
	verdictReason?: string | null
}>()

const message = useMessage()

const ShieldIcon = "carbon:security"
const CopyIcon = "carbon:copy"
const ClockIcon = "carbon:time"
const ReasonIcon = "carbon:information"

const verdict = computed<FileAnalysisVerdict>(() => props.job?.verdict || (props.result?.verdict_hint as FileAnalysisVerdict) || "clean")
const hardened = computed(() => props.job?.hardened ?? props.result?.hardened)

const verdictIcon = computed(() => {
	switch (verdict.value) {
		case "malicious":
			return "carbon:warning-alt-filled"
		case "suspicious":
			return "carbon:warning-alt"
		default:
			return "carbon:checkmark-filled"
	}
})
const verdictColorClass = computed(() => {
	switch (verdict.value) {
		case "malicious":
			return "text-red-500"
		case "suspicious":
			return "text-amber-500"
		default:
			return "text-green-500"
	}
})

const prettyType = computed(() => {
	const r = props.result
	if (!r) return ""
	const t = r.filetype && r.filetype !== "unknown" ? r.filetype : ""
	const magic = r.magic || ""
	if (t && magic) return `${t} · ${magic}`
	return t || magic || "unknown type"
})

const facts = computed(() => {
	const r = props.result
	if (!r) return []
	const list = [
		{ label: "Detected type", value: r.filetype || "unknown" },
		{ label: "Magic", value: r.magic || "—" },
		{ label: "Entropy", value: r.entropy != null ? String(r.entropy) : "—" },
		{ label: "Extension mismatch", value: r.extension_mismatch ? "yes" : "no" }
	]
	return list
})

const hashes = computed(() => {
	const r = props.result
	if (!r) return []
	return [
		{ label: "SHA256", value: r.hashes?.sha256 ?? r.sha256 ?? "—" },
		{ label: "MD5", value: r.hashes?.md5 ?? "—" },
		...(r.hashes?.imphash ? [{ label: "Imphash", value: r.hashes.imphash }] : [])
	]
})

function copy(value: string) {
	navigator.clipboard?.writeText(value).then(
		() => message.success("Copied"),
		() => message.error("Copy failed")
	)
}
</script>
