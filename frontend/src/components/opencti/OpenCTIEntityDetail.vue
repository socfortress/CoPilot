<template>
	<n-spin :show="loading" class="min-h-40">
		<div v-if="error" class="text-warning flex items-center gap-2 text-sm">
			<Icon name="carbon:warning-alt" :size="16" />
			<span>{{ error }}</span>
		</div>

		<!-- Same skeleton as the observable card, so a drawer and a lookup result read alike. -->
		<div v-else-if="entity" class="@container flex flex-col gap-5">
			<header class="flex flex-col gap-4 @lg:flex-row @lg:items-start @lg:justify-between @lg:gap-6">
				<div class="flex min-w-0 grow flex-col gap-2">
					<div class="flex flex-wrap items-center gap-x-2 gap-y-1">
						<span :class="SECTION_LABEL">{{ entity.entity_type }}</span>
						<n-tag
							v-for="marking of entity.markings"
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
						<span class="text-default min-w-0 text-lg leading-snug font-semibold break-all">
							{{ entity.name || entity.id }}
						</span>
						<button
							v-if="isCopySupported"
							type="button"
							:class="ICON_BUTTON"
							class="mt-1"
							:title="copiedText === (entity.name || entity.id) ? 'Copied' : 'Copy'"
							@click="copyText(entity.name || entity.id)"
						>
							<Icon
								:name="copiedText === (entity.name || entity.id) ? 'carbon:checkmark' : 'carbon:copy'"
								:size="15"
							/>
						</button>
						<a
							v-if="objectUrl(entity.id)"
							:href="objectUrl(entity.id) || undefined"
							target="_blank"
							rel="noopener noreferrer"
							:class="ICON_BUTTON"
							class="mt-1"
							title="Open in OpenCTI"
						>
							<Icon name="carbon:launch" :size="15" />
						</a>
					</div>

					<div v-if="metaLine.length" class="text-tertiary flex flex-wrap gap-x-3 gap-y-0.5 text-xs">
						<span v-for="item of metaLine" :key="item">{{ item }}</span>
					</div>
				</div>

				<div class="flex shrink-0 items-center gap-5">
					<div class="flex flex-col gap-1.5">
						<span :class="SECTION_LABEL">Score</span>
						<div class="flex items-center gap-3">
							<span
								class="font-mono text-2xl leading-none font-semibold tabular-nums"
								:class="scoreTextClass"
							>
								{{ entity.score ?? "—" }}
							</span>
							<div class="bg-border/50 h-1 w-20 overflow-hidden rounded-full">
								<div
									v-if="entity.score !== null"
									class="h-full rounded-full"
									:class="scoreBarClass"
									:style="{ width: `${entity.score}%` }"
								/>
							</div>
						</div>
					</div>
					<div class="flex flex-col gap-1.5">
						<span :class="SECTION_LABEL">Confidence</span>
						<span class="text-default font-mono text-2xl leading-none font-semibold tabular-nums">
							{{ entity.confidence ?? "—" }}
						</span>
					</div>
				</div>
			</header>

			<div v-if="entity.labels.length" class="flex flex-wrap gap-1.5">
				<n-tag v-for="label of entity.labels" :key="label.value" size="small" round :bordered="false">
					<span class="flex items-center gap-1.5">
						<!-- OpenCTI label colors can be near-black, so they tint a dot rather than the text. -->
						<span
							class="bg-border size-2 shrink-0 rounded-full"
							:style="{ backgroundColor: label.color || undefined }"
						></span>
						{{ label.value }}
					</span>
				</n-tag>
			</div>

			<div v-if="entity.description" class="flex flex-col items-start gap-1">
				<p
					class="text-secondary max-w-prose text-sm leading-relaxed whitespace-pre-line"
					:class="{ 'line-clamp-4': !descriptionExpanded }"
				>
					{{ entity.description }}
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

			<!-- Identity and timeline as a hairline fact grid: labels above, values in mono. -->
			<dl
				class="bg-border/40 border-border/40 grid gap-px overflow-hidden rounded-lg border @md:grid-cols-[1fr_auto_auto]"
			>
				<div class="bg-secondary flex min-w-0 flex-col gap-1 px-3 py-2.5">
					<dt :class="SECTION_LABEL">STIX id</dt>
					<dd class="flex min-w-0 items-start gap-2">
						<span class="text-default min-w-0 font-mono text-xs leading-snug break-all">
							{{ entity.standard_id || "—" }}
						</span>
						<button
							v-if="isCopySupported && entity.standard_id"
							type="button"
							:class="ICON_BUTTON"
							:title="copiedText === entity.standard_id ? 'Copied' : 'Copy'"
							@click="copyText(entity.standard_id)"
						>
							<Icon
								:name="copiedText === entity.standard_id ? 'carbon:checkmark' : 'carbon:copy'"
								:size="13"
							/>
						</button>
					</dd>
				</div>
				<div class="bg-secondary flex flex-col gap-1 px-3 py-2.5">
					<dt :class="SECTION_LABEL">Created</dt>
					<dd class="text-default font-mono text-xs whitespace-nowrap tabular-nums">
						{{ entity.created_at ? formatDate(entity.created_at, dFormats.datetime) : "—" }}
					</dd>
				</div>
				<div class="bg-secondary flex flex-col gap-1 px-3 py-2.5">
					<dt :class="SECTION_LABEL">Updated</dt>
					<dd class="text-default font-mono text-xs whitespace-nowrap tabular-nums">
						{{ entity.updated_at ? formatDate(entity.updated_at, dFormats.datetime) : "—" }}
					</dd>
				</div>
			</dl>

			<section v-if="entity.external_references.length" class="flex flex-col">
				<div class="flex items-center gap-2 pb-2">
					<Icon name="carbon:link" :size="14" class="text-secondary" />
					<span :class="SECTION_LABEL">External references ({{ entity.external_references.length }})</span>
				</div>
				<div class="divide-border/40 border-border/40 flex flex-col divide-y border-t">
					<div
						v-for="(reference, index) of entity.external_references"
						:key="index"
						class="flex items-start justify-between gap-4 py-2.5"
					>
						<div class="flex min-w-0 flex-col gap-0.5">
							<div class="flex flex-wrap items-baseline gap-x-2 text-sm">
								<span class="text-default">{{ reference.source_name || "Unnamed source" }}</span>
								<span v-if="reference.external_id" class="text-tertiary font-mono text-xs">
									{{ reference.external_id }}
								</span>
							</div>
							<span v-if="reference.description" class="text-tertiary text-xs">
								{{ reference.description }}
							</span>
							<span
								v-if="reference.url"
								class="text-tertiary truncate font-mono text-xs"
								:title="reference.url"
							>
								{{ reference.url }}
							</span>
						</div>
						<a
							v-if="reference.url"
							:href="reference.url"
							target="_blank"
							rel="noopener noreferrer"
							:class="ICON_BUTTON"
							class="mt-0.5"
							title="Open reference"
						>
							<Icon name="carbon:launch" :size="14" />
						</a>
					</div>
				</div>
			</section>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { OpenCTIEntity } from "@/types/opencti"
import { useClipboard } from "@vueuse/core"
import axios from "axios"
import { NSpin, NTag } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { SECTION_LABEL } from "@/components/common/section-label"
import { useOpenCTIAvailability } from "@/composables/useOpenCTIAvailability"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import { markingType, scoreColor } from "./utils"

const { entityId } = defineProps<{
	/** OpenCTI internal id or STIX standard_id */
	entityId: string
}>()

const ICON_BUTTON = "text-tertiary hover:text-primary flex shrink-0 transition-colors"

// Past this many characters a description is clamped; the button only appears
// when there is actually something hidden behind the clamp.
const DESCRIPTION_CLAMP_CHARS = 320

const dFormats = useSettingsStore().dateFormat
const { objectUrl } = useOpenCTIAvailability()
const { copy, isSupported: isCopySupported } = useClipboard()

const loading = ref(false)
const entity = ref<OpenCTIEntity | null>(null)
const error = ref("")
const copiedText = ref<string | null>(null)
const descriptionExpanded = ref(false)

const metaLine = computed(() => {
	if (!entity.value) return []
	const items: string[] = []
	if (entity.value.created_by) items.push(`by ${entity.value.created_by}`)
	return items
})

const descriptionIsLong = computed(() => {
	const text = entity.value?.description
	return !!text && (text.length > DESCRIPTION_CLAMP_CHARS || text.split("\n").length > 4)
})

const scoreTextClass = computed(() => {
	if (!entity.value || entity.value.score === null) return "text-tertiary"
	const color = scoreColor(entity.value.score)
	return color === "danger" ? "text-error" : color === "warning" ? "text-warning" : "text-default"
})

const scoreBarClass = computed(() => {
	const color = scoreColor(entity.value?.score)
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

let controller: AbortController | null = null

function load(id: string) {
	controller?.abort()
	const current = new AbortController()
	controller = current
	loading.value = true
	error.value = ""
	entity.value = null
	descriptionExpanded.value = false

	Api.opencti
		.getEntity(id, current.signal)
		.then(res => {
			entity.value = res.data.entity
		})
		.catch(err => {
			if (axios.isCancel(err)) return
			error.value = getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later."
		})
		.finally(() => {
			// A superseded request must not end the spinner of the one that replaced it.
			if (controller === current) loading.value = false
		})
}

watch(() => entityId, load, { immediate: true })
</script>
