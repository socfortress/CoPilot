<template>
	<article class="bg-secondary border-border/60 @container flex flex-col overflow-hidden rounded-lg border">
		<!--
			Header: what it is, what it's called, how bad it is. Everything else is
			supporting context and lives below the fold. The score is a meter rather
			than a badge because 0–100 only means something against its scale.
		-->
		<header
			class="border-border/60 flex flex-col gap-4 border-b p-4 @2xl:flex-row @2xl:items-start @2xl:justify-between @2xl:gap-6"
		>
			<div class="flex min-w-0 grow flex-col gap-2">
				<div class="flex flex-wrap items-center gap-x-2 gap-y-1">
					<Icon :name="typeIcon" :size="14" class="text-secondary" />
					<span :class="SECTION_LABEL">{{ observable.entity_type }}</span>
					<n-tag
						v-for="marking of observable.markings"
						:key="marking"
						size="tiny"
						:type="markingType(marking)"
						:bordered="false"
						class="font-mono"
					>
						{{ marking }}
					</n-tag>
				</div>

				<div class="flex min-w-0 items-start gap-2">
					<span class="text-default min-w-0 font-mono text-base leading-snug break-all @2xl:text-lg">
						{{ displayValue }}
					</span>
					<button
						v-if="isCopySupported && displayValue !== '-'"
						type="button"
						class="text-tertiary hover:text-primary mt-0.5 shrink-0 transition-colors"
						:title="copiedText === displayValue ? 'Copied' : 'Copy'"
						@click="copyText(displayValue)"
					>
						<Icon :name="copiedText === displayValue ? 'carbon:checkmark' : 'carbon:copy'" :size="15" />
					</button>
				</div>

				<div v-if="metaLine.length" class="text-tertiary flex flex-wrap gap-x-3 gap-y-0.5 text-xs">
					<span v-for="item of metaLine" :key="item">{{ item }}</span>
				</div>
			</div>

			<div class="flex shrink-0 items-center justify-between gap-5 @2xl:flex-col @2xl:items-end @2xl:gap-3">
				<div class="flex flex-col gap-1.5 @2xl:items-end">
					<span :class="SECTION_LABEL">Score</span>
					<div class="flex items-center gap-3 @2xl:flex-row-reverse">
						<span
							class="font-mono text-2xl leading-none font-semibold tabular-nums"
							:class="scoreTextClass"
						>
							{{ observable.score ?? "—" }}
						</span>
						<div class="bg-border/50 h-1 w-24 overflow-hidden rounded-full">
							<div
								v-if="observable.score !== null"
								class="h-full rounded-full transition-[width]"
								:class="scoreBarClass"
								:style="{ width: `${observable.score}%` }"
							/>
						</div>
					</div>
				</div>

				<a
					v-if="objectUrl(observable.id)"
					:href="objectUrl(observable.id) || undefined"
					target="_blank"
					rel="noopener noreferrer"
					class="text-secondary hover:text-primary flex items-center gap-1 text-xs whitespace-nowrap transition-colors"
				>
					Open in OpenCTI
					<Icon name="carbon:launch" :size="12" />
				</a>
			</div>
		</header>

		<div v-if="observable.labels.length || observable.description" class="flex flex-col gap-3 p-4">
			<div v-if="observable.labels.length" class="flex flex-wrap gap-1.5">
				<n-tag v-for="label of observable.labels" :key="label.value" size="small" round :bordered="false">
					<span class="flex items-center gap-1.5 pr-0.5">
						<!-- OpenCTI label colors can be near-black, so they tint a dot rather than the text. -->
						<span
							class="bg-border size-2 shrink-0 rounded-full"
							:style="{ backgroundColor: label.color || undefined }"
						></span>
						{{ label.value }}
					</span>
				</n-tag>
			</div>

			<div v-if="observable.description" class="flex flex-col items-start gap-1">
				<p
					class="text-secondary max-w-prose text-sm leading-relaxed whitespace-pre-line"
					:class="{ 'line-clamp-3': !descriptionExpanded }"
				>
					{{ observable.description }}
				</p>
				<button
					v-if="descriptionIsLong"
					type="button"
					class="text-tertiary hover:text-primary text-xs transition-colors"
					@click="descriptionExpanded = !descriptionExpanded"
				>
					{{ descriptionExpanded ? "Show less" : "Show more" }}
				</button>
			</div>
		</div>

		<!-- File observables: every hash the platform holds, each one copyable. -->
		<div v-if="observable.hashes.length" class="divide-border/40 border-border/40 flex flex-col divide-y border-t">
			<div
				v-for="hash of observable.hashes"
				:key="hash.algorithm"
				class="flex items-center gap-3 px-4 py-2 font-mono text-xs"
			>
				<span class="text-tertiary w-16 shrink-0 uppercase">{{ hash.algorithm }}</span>
				<span class="text-default min-w-0 grow break-all">{{ hash.hash }}</span>
				<button
					v-if="isCopySupported"
					type="button"
					class="text-tertiary hover:text-primary shrink-0 transition-colors"
					:title="copiedText === hash.hash ? 'Copied' : 'Copy'"
					@click="copyText(hash.hash)"
				>
					<Icon :name="copiedText === hash.hash ? 'carbon:checkmark' : 'carbon:copy'" :size="14" />
				</button>
			</div>
		</div>

		<!--
			Two panels side by side once there is room; a hairline grid keeps them
			aligned without adding boxes inside the box.
		-->
		<div class="bg-border/40 border-border/40 grid gap-px border-t @3xl:grid-cols-2">
			<section class="bg-secondary flex min-w-0 flex-col">
				<div class="flex items-center gap-2 px-4 pt-3 pb-2">
					<Icon name="carbon:radar" :size="14" class="text-secondary" />
					<span :class="SECTION_LABEL">Indicators ({{ observable.indicators_count }})</span>
				</div>

				<div v-if="!observable.indicators.length" class="text-tertiary px-4 pb-4 text-sm">None</div>
				<div v-else class="divide-border/40 border-border/40 flex flex-col divide-y border-t">
					<div
						v-for="indicator of observable.indicators"
						:key="indicator.id"
						class="flex flex-col flex-wrap gap-1.5 px-4 py-2.5 @xl:flex-row @xl:items-start @xl:justify-between @xl:gap-x-4"
					>
						<span class="text-default min-w-40 grow font-mono text-sm leading-snug break-all">
							{{ indicator.pattern || indicator.name || indicator.id }}
						</span>

						<div class="flex shrink-0 items-center gap-3">
							<div class="flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-xs">
								<span v-if="indicator.score !== null" :class="scoreClass(indicator.score)">
									score {{ indicator.score }}
								</span>
								<span v-if="indicator.confidence !== null" class="text-tertiary">
									conf {{ indicator.confidence }}
								</span>
								<span class="flex items-center gap-1.5">
									<span
										class="size-1.5 shrink-0 rounded-full"
										:class="VALIDITY_DOT[indicatorValidity(indicator)]"
									/>
									<span class="text-tertiary">
										{{ VALIDITY_LABEL[indicatorValidity(indicator)] }}
									</span>
									<span
										v-if="indicator.valid_until && indicatorValidity(indicator) !== 'revoked'"
										class="text-secondary"
									>
										{{ formatDate(indicator.valid_until, dFormats.date) }}
									</span>
								</span>
							</div>
							<a
								v-if="objectUrl(indicator.id)"
								:href="objectUrl(indicator.id) || undefined"
								target="_blank"
								rel="noopener noreferrer"
								:class="OPEN_LINK"
								title="Open in OpenCTI"
							>
								<Icon name="carbon:launch" :size="14" />
							</a>
						</div>
					</div>
					<div
						v-if="observable.indicators_count > observable.indicators.length"
						class="text-tertiary px-4 py-2 text-xs"
					>
						+{{ observable.indicators_count - observable.indicators.length }} more in OpenCTI
					</div>
				</div>
			</section>

			<section class="bg-secondary flex min-w-0 flex-col">
				<div class="flex items-center gap-2 px-4 pt-3 pb-2">
					<Icon name="carbon:notebook" :size="14" class="text-secondary" />
					<span :class="SECTION_LABEL">Reports ({{ observable.reports_count }})</span>
				</div>

				<div v-if="!observable.reports.length" class="text-tertiary px-4 pb-4 text-sm">None</div>
				<div v-else class="divide-border/40 border-border/40 flex flex-col divide-y border-t">
					<div
						v-for="report of observable.reports"
						:key="report.id"
						class="flex items-center justify-between gap-4 px-4 py-2.5"
					>
						<span
							class="text-default min-w-0 grow text-sm leading-snug"
							:class="{ 'text-tertiary font-mono text-xs': !report.name }"
						>
							{{ report.name || report.id }}
						</span>
						<div class="flex shrink-0 items-center gap-3">
							<span class="text-tertiary font-mono text-xs tabular-nums">
								{{ report.published ? formatDate(report.published, dFormats.date) : "—" }}
							</span>
							<a
								v-if="objectUrl(report.id)"
								:href="objectUrl(report.id) || undefined"
								target="_blank"
								rel="noopener noreferrer"
								:class="OPEN_LINK"
								title="Open in OpenCTI"
							>
								<Icon name="carbon:launch" :size="14" />
							</a>
						</div>
					</div>
					<div
						v-if="observable.reports_count > observable.reports.length"
						class="text-tertiary px-4 py-2 text-xs"
					>
						+{{ observable.reports_count - observable.reports.length }} more in OpenCTI
					</div>
				</div>
			</section>
		</div>
	</article>
</template>

<script setup lang="ts">
import type { OpenCTIObservable } from "@/types/opencti"
import { useClipboard } from "@vueuse/core"
import { NTag } from "naive-ui"
import { computed, ref } from "vue"
import Icon from "@/components/common/Icon.vue"
import { SECTION_LABEL } from "@/components/common/section-label"
import { useOpenCTIAvailability } from "@/composables/useOpenCTIAvailability"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"
import { indicatorValidity, markingType, scoreColor, VALIDITY_DOT, VALIDITY_LABEL } from "./utils"

const { observable } = defineProps<{
	observable: OpenCTIObservable
}>()

// Rows are plain text; the way out to OpenCTI is always this icon at the row's
// end, so a reader never has to guess which words are links.
const OPEN_LINK = "text-tertiary hover:text-primary flex shrink-0 transition-colors"

// Past this many characters a description is clamped; the button only appears
// when there is actually something hidden behind the clamp.
const DESCRIPTION_CLAMP_CHARS = 240

const TYPE_ICONS: Record<string, string> = {
	"IPv4-Addr": "carbon:network-3",
	"IPv6-Addr": "carbon:network-3",
	"Domain-Name": "carbon:content-delivery-network",
	Hostname: "carbon:content-delivery-network",
	Url: "carbon:link",
	StixFile: "carbon:document",
	"Email-Addr": "carbon:email"
}

const dFormats = useSettingsStore().dateFormat
const { objectUrl } = useOpenCTIAvailability()
const { copy, isSupported: isCopySupported } = useClipboard()

const copiedText = ref<string | null>(null)
const descriptionExpanded = ref(false)

const displayValue = computed(() => observable.value || observable.file_name || "-")
const typeIcon = computed(() => TYPE_ICONS[observable.entity_type] || "carbon:fingerprint-recognition")
const descriptionIsLong = computed(
	() =>
		!!observable.description &&
		(observable.description.length > DESCRIPTION_CLAMP_CHARS || observable.description.includes("\n"))
)

const metaLine = computed(() => {
	const items: string[] = []
	if (observable.created_by) items.push(`by ${observable.created_by}`)
	if (observable.created_at) items.push(`added ${formatDate(observable.created_at, dFormats.date)}`)
	if (observable.updated_at && observable.updated_at !== observable.created_at) {
		items.push(`updated ${formatDate(observable.updated_at, dFormats.date)}`)
	}
	return items
})

function scoreClass(score: number | null): string {
	const color = scoreColor(score)
	return color === "danger" ? "text-error" : color === "warning" ? "text-warning" : "text-secondary"
}

const scoreTextClass = computed(() =>
	observable.score === null ? "text-tertiary" : scoreClass(observable.score).replace("text-secondary", "text-default")
)

const scoreBarClass = computed(() => {
	const color = scoreColor(observable.score)
	return color === "danger" ? "bg-error" : color === "warning" ? "bg-warning" : "bg-success"
})

let copiedTimer: ReturnType<typeof setTimeout> | null = null

function copyText(text: string) {
	copy(text).then(() => {
		copiedText.value = text
		if (copiedTimer) clearTimeout(copiedTimer)
		copiedTimer = setTimeout(() => {
			copiedText.value = null
		}, 1500)
	})
}
</script>
