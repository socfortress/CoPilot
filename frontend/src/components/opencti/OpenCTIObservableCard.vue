<template>
	<div class="bg-secondary flex flex-col gap-3 rounded-lg border p-4">
		<div class="flex items-start justify-between gap-3">
			<div class="flex min-w-0 flex-col gap-0.5">
				<div class="text-secondary font-mono text-xs">{{ observable.entity_type }}</div>
				<div class="font-mono break-all">{{ observable.value || observable.file_name || "-" }}</div>
			</div>
			<Badge type="splitted" size="small" bright :color="scoreColor(observable.score)" class="shrink-0">
				<template #label>Score</template>
				<template #value>{{ observable.score ?? "-" }}</template>
			</Badge>
		</div>

		<div v-if="observable.markings.length || observable.created_by" class="flex flex-wrap items-center gap-2">
			<n-tag v-for="marking of observable.markings" :key="marking" size="small" :type="markingType(marking)">
				{{ marking }}
			</n-tag>
			<span v-if="observable.created_by" class="text-secondary text-sm">by {{ observable.created_by }}</span>
		</div>

		<div v-if="observable.labels.length" class="flex flex-wrap gap-1.5">
			<n-tag v-for="label of observable.labels" :key="label.value" size="small" round>
				<span class="flex items-center gap-1.5">
					<!-- OpenCTI label colours can be near-black, so they tint a dot rather than the text. -->
					<span
						class="size-2 shrink-0 rounded-full"
						:style="{ backgroundColor: label.color || undefined }"
					></span>
					{{ label.value }}
				</span>
			</n-tag>
		</div>

		<div v-if="observable.description" class="text-sm">{{ observable.description }}</div>

		<div v-if="observable.hashes.length > 1" class="flex flex-col gap-1">
			<div v-for="hash of observable.hashes" :key="hash.algorithm" class="flex gap-2 text-xs">
				<span class="text-secondary w-16 shrink-0 font-mono">{{ hash.algorithm }}</span>
				<span class="font-mono break-all">{{ hash.hash }}</span>
			</div>
		</div>

		<div class="flex flex-col gap-1.5">
			<div class="text-secondary text-xs tracking-wide uppercase">
				Indicators ({{ observable.indicators_count }})
			</div>
			<div v-if="!observable.indicators.length" class="text-secondary text-sm">None</div>
			<div
				v-for="indicator of observable.indicators"
				:key="indicator.id"
				class="flex flex-col gap-1 border-l-2 pl-3"
			>
				<div class="flex flex-wrap items-center gap-2">
					<component
						:is="objectUrl(indicator.id) ? 'a' : 'span'"
						:href="objectUrl(indicator.id) || undefined"
						target="_blank"
						rel="noopener noreferrer"
						class="font-mono text-sm break-all"
					>
						{{ indicator.pattern || indicator.name || indicator.id }}
					</component>
					<n-tag v-if="indicator.revoked" size="small" type="error">revoked</n-tag>
				</div>
				<div class="text-secondary flex flex-wrap gap-x-3 text-xs">
					<span v-if="indicator.score !== null">score {{ indicator.score }}</span>
					<span v-if="indicator.confidence !== null">confidence {{ indicator.confidence }}</span>
					<span v-if="indicator.valid_until">
						{{ isExpired(indicator.valid_until) ? "expired" : "valid until" }}
						{{ formatDate(indicator.valid_until, dFormats.date) }}
					</span>
				</div>
			</div>
		</div>

		<div class="flex flex-col gap-1.5">
			<div class="text-secondary text-xs tracking-wide uppercase">Reports ({{ observable.reports_count }})</div>
			<div v-if="!observable.reports.length" class="text-secondary text-sm">None</div>
			<div
				v-for="report of observable.reports"
				:key="report.id"
				class="flex items-baseline justify-between gap-3"
			>
				<component
					:is="objectUrl(report.id) ? 'a' : 'span'"
					:href="objectUrl(report.id) || undefined"
					target="_blank"
					rel="noopener noreferrer"
					class="text-sm"
				>
					{{ report.name || report.id }}
				</component>
				<span v-if="report.published" class="text-secondary shrink-0 text-xs">
					{{ formatDate(report.published, dFormats.date) }}
				</span>
			</div>
		</div>

		<div v-if="objectUrl(observable.id)" class="flex justify-end">
			<a :href="objectUrl(observable.id) || undefined" target="_blank" rel="noopener noreferrer" class="text-sm">
				Open in OpenCTI
			</a>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { BadgeColor } from "@/components/common/Badge.vue"
import type { OpenCTIObservable } from "@/types/opencti"
import { NTag } from "naive-ui"
import Badge from "@/components/common/Badge.vue"
import { useOpenCTIAvailability } from "@/composables/useOpenCTIAvailability"
import { useSettingsStore } from "@/stores/settings"
import dayjs from "@/utils/dayjs"
import { formatDate } from "@/utils/format"

const { observable } = defineProps<{
	observable: OpenCTIObservable
}>()

const dFormats = useSettingsStore().dateFormat
const { objectUrl } = useOpenCTIAvailability()

function scoreColor(score: number | null): BadgeColor | undefined {
	if (score === null) return undefined
	if (score >= 75) return "danger"
	if (score >= 50) return "warning"
	return undefined
}

function markingType(marking: string): "error" | "warning" | "success" | "default" {
	const tlp = marking.toUpperCase()
	if (tlp.startsWith("TLP:RED")) return "error"
	if (tlp.startsWith("TLP:AMBER")) return "warning"
	if (tlp.startsWith("TLP:GREEN")) return "success"
	return "default"
}

function isExpired(date: string): boolean {
	return dayjs(date).isBefore(dayjs())
}
</script>
