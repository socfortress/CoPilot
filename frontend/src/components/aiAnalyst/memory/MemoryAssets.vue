<template>
	<div class="grid grid-cols-1 gap-4 lg:grid-cols-5" data-testid="talon-memory-assets">
		<SocPanel title="Assets Talon remembers" class="lg:col-span-2" flush>
			<div class="flex flex-col gap-2 p-3">
				<n-input
					v-model:value="search"
					size="small"
					clearable
					:maxlength="200"
					placeholder="Filter by name"
					:input-props="{ 'aria-label': 'Filter assets' }"
					data-testid="talon-memory-asset-search"
				>
					<template #prefix><Icon name="carbon:search" :size="14" /></template>
				</n-input>
				<MemoryProblem v-if="problem" :state="problem" @retry="load()" />
				<div v-else-if="loading && !assets.length" class="flex justify-center py-8">
					<n-spin size="small" />
				</div>
				<n-empty
					v-else-if="!assets.length"
					:description="query ? 'No asset matches' : 'Talon remembers no assets for this customer yet'"
					class="py-8"
					data-testid="talon-memory-assets-empty"
				/>
				<ul v-else class="flex list-none flex-col p-0" :class="{ 'opacity-60': loading }" aria-label="Assets">
					<li v-for="asset of assets" :key="asset.asset">
						<button
							type="button"
							class="hover:bg-secondary focus-visible:bg-secondary flex w-full items-center justify-between gap-3 rounded-md px-2 py-1.5 text-left disabled:cursor-not-allowed disabled:opacity-60"
							:class="{ 'bg-secondary': selected === asset.asset }"
							:aria-pressed="selected === asset.asset"
							:disabled="!asset.openable"
							:title="asset.openable ? undefined : 'This asset name can\'t be opened from CoPilot'"
							data-testid="talon-memory-asset"
							:data-asset="asset.asset"
							@click="select(asset.asset)"
						>
							<span class="min-w-0 truncate font-mono text-sm">
								<bdi>{{ asset.asset }}</bdi>
							</span>
							<span class="text-tertiary shrink-0 text-xs tabular-nums">
								{{ formatCount(asset.alerts) }} alerts · IOCs: {{ formatIocs(asset.iocs) }}
							</span>
						</button>
					</li>
				</ul>
			</div>
		</SocPanel>

		<SocPanel :title="selected ? `Timeline: ${selected}` : 'Timeline'" class="lg:col-span-3">
			<p v-if="!selected" class="text-tertiary py-8 text-center text-sm">
				Choose an asset to see what Talon learnt about it, and when.
			</p>
			<MemoryProblem v-else-if="timelineProblem" :state="timelineProblem" @retry="loadTimeline()" />
			<div v-else-if="timelineLoading" class="flex justify-center py-8"><n-spin size="small" /></div>
			<n-empty
				v-else-if="!facts.length"
				description="Talon has no facts about this asset"
				class="py-8"
				data-testid="talon-memory-timeline-empty"
			/>
			<n-timeline v-else data-testid="talon-memory-timeline">
				<n-timeline-item
					v-for="(fact, index) of facts"
					:key="index"
					:type="fact.valid_to ? 'default' : 'info'"
					:time="span(fact)"
					data-testid="talon-memory-fact"
				>
					<span class="inline-flex flex-wrap items-baseline gap-x-1 text-sm break-words">
						<bdi class="font-mono">{{ fact.subject ?? "?" }}</bdi>
						<span class="text-secondary">{{ fact.predicate ?? "—" }}</span>
						<bdi>{{ fact.object ?? "?" }}</bdi>
					</span>
					<n-tag v-if="fact.valid_to" size="tiny" :bordered="false" class="ml-2">no longer true</n-tag>
				</n-timeline-item>
			</n-timeline>
		</SocPanel>
	</div>
</template>

<script setup lang="ts">
// The assets Talon remembers for a customer, and one asset's timeline: the facts Talon learnt,
// oldest first, each with the time it became true and, once replaced, when it stopped.
import type { TalonMemoryFailure } from "@/api/endpoints/talonMemory"
import type { TalonMemoryAsset, TalonMemoryFact } from "@/types/talonMemory"
import { watchDebounced } from "@vueuse/core"
import { NEmpty, NInput, NSpin, NTag, NTimeline, NTimelineItem } from "naive-ui"
import { computed, onBeforeUnmount, ref, watch } from "vue"
import Api from "@/api"
import { memoryFailure } from "@/api/endpoints/talonMemory"
import Icon from "@/components/common/Icon.vue"
import SocPanel from "@/components/socManagement/ui/SocPanel.vue"
import { formatTime } from "../health/health"
import { formatCount, formatIocs, problemState, SEARCH_DEBOUNCE_MS } from "./memory"
import MemoryProblem from "./MemoryProblem.vue"

const { customerCode } = defineProps<{ customerCode: string }>()

const search = ref<string | null>(null)
const query = ref<string | null>(null)
const assets = ref<TalonMemoryAsset[]>([])
const failure = ref<TalonMemoryFailure | null>(null)
const loading = ref(false)
const selected = ref<string | null>(null)
const facts = ref<TalonMemoryFact[]>([])
const timelineFailure = ref<TalonMemoryFailure | null>(null)
const timelineLoading = ref(false)
let controller: AbortController | null = null
let timelineController: AbortController | null = null

const problem = computed(() => problemState(failure.value))
const timelineProblem = computed(() => problemState(timelineFailure.value))

function span(fact: TalonMemoryFact) {
	const from = fact.valid_from ? formatTime(fact.valid_from) : "since ?"
	return fact.valid_to ? `${from} → ${formatTime(fact.valid_to)}` : `${from} → now`
}

async function load() {
	controller?.abort()
	const own = new AbortController()
	controller = own
	loading.value = true
	failure.value = null
	try {
		const { data } = await Api.talonMemory.listAssets(customerCode, { q: query.value, limit: 100 }, own.signal)
		if (controller !== own) return
		assets.value = data.items ?? []
	} catch (err) {
		if (controller !== own || own.signal.aborted) return
		assets.value = []
		failure.value = memoryFailure(err)
	} finally {
		if (controller === own) loading.value = false
	}
}

async function loadTimeline() {
	timelineController?.abort()
	facts.value = []
	timelineFailure.value = null
	const asset = selected.value
	if (!asset) return
	const own = new AbortController()
	timelineController = own
	timelineLoading.value = true
	try {
		const { data } = await Api.talonMemory.getAssetTimeline(customerCode, asset, own.signal)
		if (timelineController !== own) return
		facts.value = [...(data.facts ?? [])].sort((a, b) => (a.valid_from ?? "").localeCompare(b.valid_from ?? ""))
	} catch (err) {
		if (timelineController !== own || own.signal.aborted) return
		timelineFailure.value = memoryFailure(err)
	} finally {
		if (timelineController === own) timelineLoading.value = false
	}
}

function select(asset: string) {
	selected.value = asset
	loadTimeline()
}

watchDebounced(
	search,
	value => {
		const text = (value ?? "").trim()
		query.value = text || null
	},
	{ debounce: SEARCH_DEBOUNCE_MS }
)
watch(
	() => customerCode,
	() => {
		selected.value = null
		facts.value = []
	}
)
watch([() => customerCode, query], () => load(), { immediate: true })
onBeforeUnmount(() => {
	controller?.abort()
	timelineController?.abort()
})
</script>
