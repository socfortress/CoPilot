<template>
	<p v-if="unsupported" class="text-tertiary m-0 text-xs" data-testid="knowledge-sees-unsupported">
		{{ UNSUPPORTED_TEXT }}
	</p>

	<n-card v-else size="small" data-testid="knowledge-sees">
		<template #header>
			<div class="flex items-center gap-2">
				<Icon :name="SeesIcon" :size="16" />
				<span>What Talon sees</span>
			</div>
		</template>

		<div v-if="loading" class="flex items-center gap-2" data-testid="knowledge-sees-loading">
			<n-spin :size="14" />
			<span class="text-secondary text-sm">Reading what Talon has measured…</span>
		</div>

		<n-alert v-else-if="failure" type="error" :bordered="false" data-testid="knowledge-sees-failure">
			<div class="flex flex-wrap items-center justify-between gap-3">
				<span>{{ failure.detail }}</span>
				<n-button size="small" data-testid="knowledge-sees-retry" @click="load()">Try again</n-button>
			</div>
		</n-alert>

		<p
			v-else-if="seen?.status === 'no_profile'"
			class="text-secondary m-0 text-sm"
			data-testid="knowledge-sees-no-profile"
		>
			{{ NO_PROFILE_TEXT }}
		</p>

		<n-alert
			v-else-if="seen?.status === 'no_sources'"
			type="warning"
			:bordered="false"
			data-testid="knowledge-sees-no-verified-sources"
		>
			{{ NO_VERIFIED_SOURCES_TEXT }}
		</n-alert>

		<n-alert
			v-else-if="seen?.status === 'no_tenant_map'"
			type="warning"
			:bordered="false"
			data-testid="knowledge-sees-no-tenant-map"
		>
			{{ NO_TENANT_MAP_TEXT }}
		</n-alert>

		<div v-else-if="seen" class="flex flex-col gap-7" data-testid="knowledge-sees-measured">
			<p class="text-secondary m-0 text-sm" data-testid="knowledge-sees-when">{{ measured }}</p>

			<section class="flex flex-col gap-2">
				<span class="text-secondary font-mono text-[10px] tracking-[0.14em] uppercase">Coverage</span>
				<ul class="m-0 flex list-none flex-col gap-1 p-0">
					<li
						v-for="row of coverage"
						:key="row.category"
						class="flex items-center gap-3 text-sm"
						:data-testid="`knowledge-sees-coverage-${row.category}`"
					>
						<span class="w-20 shrink-0">{{ row.label }}</span>
						<n-tag size="small" :type="STATE_TAGS[row.state]" :bordered="false">{{ row.word }}</n-tag>
					</li>
				</ul>
			</section>

			<section class="flex flex-col gap-2">
				<span class="text-secondary font-mono text-[10px] tracking-[0.14em] uppercase">Log sources</span>
				<p v-if="sources.length" class="text-default m-0 text-xs" data-testid="knowledge-sees-fields-note">
					{{ fieldsNote }}
				</p>
				<CardEntity
					v-for="source of sources"
					:key="source.pattern"
					embedded
					size="small"
					data-testid="knowledge-sees-source"
				>
					<template #headerMain>
						<div class="flex flex-wrap items-center gap-2">
							<span
								class="text-default font-mono font-medium break-all"
								data-testid="knowledge-sees-source-pattern"
							>
								{{ source.pattern }}
							</span>
							<n-tag
								v-if="source.quiet"
								size="small"
								type="warning"
								:bordered="false"
								data-testid="knowledge-sees-source-quiet"
							>
								Quiet
							</n-tag>
						</div>
					</template>

					<template #default>
						<div class="flex flex-col gap-1 text-sm">
							<div v-if="source.categories.length" class="flex flex-wrap gap-1">
								<span class="font-medium">Categories:</span>
								<span>{{ source.categories.join(", ") }}</span>
							</div>
							<p
								v-if="source.events"
								class="text-secondary m-0"
								data-testid="knowledge-sees-source-events"
							>
								{{ source.events }}
							</p>
							<p
								v-if="source.carried"
								class="text-warning m-0"
								data-testid="knowledge-sees-source-carried"
							>
								{{ source.carried }}
							</p>
							<div
								v-if="source.fields.length"
								class="grid grid-cols-[repeat(auto-fill,minmax(15rem,1fr))] items-start gap-x-4 gap-y-1"
							>
								<div
									v-for="field of source.fields"
									:key="field.role"
									class="flex flex-wrap gap-1"
									:data-testid="`knowledge-sees-field-${field.role}`"
								>
									<span class="font-medium">{{ field.label }}:</span>
									<code v-for="name of field.names" :key="name" class="break-all">{{ name }}</code>
								</div>
							</div>
						</div>
					</template>
				</CardEntity>
				<p v-if="!sources.length" class="text-tertiary m-0 text-sm" data-testid="knowledge-sees-no-sources">
					{{ NO_SOURCES_TEXT }}
				</p>
			</section>

			<section
				v-if="seen.not_measured.length"
				class="flex flex-col gap-2"
				data-testid="knowledge-sees-not-measured"
			>
				<span class="text-secondary font-mono text-[10px] tracking-[0.14em] uppercase">Not measured</span>
				<p class="text-default m-0 text-xs">{{ NOT_MEASURED_ABOUT }}</p>
				<div class="flex flex-wrap gap-1">
					<code v-for="pattern of seen.not_measured" :key="pattern" class="font-mono break-all">
						{{ pattern }}
					</code>
				</div>
			</section>
		</div>
	</n-card>
</template>

<script setup lang="ts">
import type { CoverageState } from "./sees"
import type { TalonMemoryFailure } from "@/api/endpoints/talonMemory"
import type { TalonSees } from "@/types/customer-knowledge"
import { NAlert, NButton, NCard, NSpin, NTag } from "naive-ui"
import { computed, onBeforeUnmount, ref, watch } from "vue"
import Api from "@/api"
import { memoryFailure } from "@/api/endpoints/talonMemory"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"
import {
	coverageRows,
	fieldsLine,
	isUnsupported,
	measuredLine,
	NO_PROFILE_TEXT,
	NO_SOURCES_TEXT,
	NO_TENANT_MAP_TEXT,
	NO_VERIFIED_SOURCES_TEXT,
	NOT_MEASURED_ABOUT,
	sourceView,
	UNSUPPORTED_TEXT
} from "./sees"

const { customerCode } = defineProps<{
	customerCode: string
}>()

const SeesIcon = "carbon:view"

const STATE_TAGS: Record<CoverageState, "success" | "warning" | "default"> = {
	available: "success",
	degraded: "warning",
	unavailable: "default",
	not_measured: "default"
}

const dFormats = useSettingsStore().dateFormat

// Null until an answer arrives. Its own request and its own state: the facts never wait on this.
const seen = ref<TalonSees | null>(null)
const loading = ref(false)
const failure = ref<TalonMemoryFailure | null>(null)

const unsupported = computed(() => isUnsupported(failure.value))
const coverage = computed(() => coverageRows(seen.value?.coverage ?? null))
const sources = computed(
	() =>
		seen.value?.sources.map(source =>
			sourceView(source, seen.value?.event_days ?? null, seen.value?.measured_at ?? null, when)
		) ?? []
)
const fieldsNote = computed(() => fieldsLine(seen.value?.field_days ?? null))
const measured = computed(() => measuredLine(seen.value?.measured_at ?? null, when))

function when(moment: string): string {
	return String(formatDate(moment, dFormats.datetime))
}

let controller: AbortController | null = null

async function load() {
	controller?.abort()
	const current = new AbortController()
	controller = current
	loading.value = true
	failure.value = null
	try {
		const res = await Api.customerKnowledge.whatTalonSees(customerCode, current.signal)
		if (current.signal.aborted) return
		seen.value = res.data
	} catch (err) {
		if (current.signal.aborted) return
		failure.value = memoryFailure(err)
	} finally {
		if (!current.signal.aborted) loading.value = false
	}
}

watch(
	() => customerCode,
	() => {
		seen.value = null
		load()
	},
	{ immediate: true }
)
onBeforeUnmount(() => controller?.abort())
</script>
