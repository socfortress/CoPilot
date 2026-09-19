<template>
	<n-spin :show="loading" class="min-h-40">
		<div v-if="error" class="bg-secondary border-error rounded-lg border px-4 py-2.5">{{ error }}</div>

		<div v-else-if="entity" class="flex flex-col gap-4">
			<div class="flex items-start justify-between gap-3">
				<div class="flex min-w-0 flex-col gap-0.5">
					<div class="text-secondary font-mono text-xs">{{ entity.entity_type }}</div>
					<div class="text-lg font-semibold break-all">{{ entity.name || entity.id }}</div>
				</div>
				<div class="flex shrink-0 gap-2">
					<Badge
						v-if="entity.score !== null"
						type="splitted"
						size="small"
						bright
						:color="scoreColor(entity.score)"
					>
						<template #label>Score</template>
						<template #value>{{ entity.score }}</template>
					</Badge>
					<Badge v-if="entity.confidence !== null" type="splitted" size="small">
						<template #label>Confidence</template>
						<template #value>{{ entity.confidence }}</template>
					</Badge>
				</div>
			</div>

			<div v-if="entity.markings.length || entity.created_by" class="flex flex-wrap items-center gap-2">
				<n-tag v-for="marking of entity.markings" :key="marking" size="small" :type="markingType(marking)">
					{{ marking }}
				</n-tag>
				<span v-if="entity.created_by" class="text-secondary text-sm">by {{ entity.created_by }}</span>
			</div>

			<div v-if="entity.labels.length" class="flex flex-wrap gap-1.5">
				<n-tag v-for="label of entity.labels" :key="label.value" size="small" round>
					<span class="flex items-center gap-1.5">
						<span
							class="size-2 shrink-0 rounded-full"
							:style="{ backgroundColor: label.color || undefined }"
						></span>
						{{ label.value }}
					</span>
				</n-tag>
			</div>

			<p v-if="entity.description" class="text-sm whitespace-pre-line">{{ entity.description }}</p>

			<div class="grid-auto-fit-200 grid gap-2">
				<CardKV>
					<template #key>STIX id</template>
					<template #value>
						<span class="font-mono text-xs break-all">{{ entity.standard_id || "-" }}</span>
					</template>
				</CardKV>
				<CardKV>
					<template #key>created</template>
					<template #value>
						{{ entity.created_at ? formatDate(entity.created_at, dFormats.datetime) : "-" }}
					</template>
				</CardKV>
				<CardKV>
					<template #key>updated</template>
					<template #value>
						{{ entity.updated_at ? formatDate(entity.updated_at, dFormats.datetime) : "-" }}
					</template>
				</CardKV>
			</div>

			<div v-if="entity.external_references.length" class="flex flex-col gap-1.5">
				<div class="text-secondary text-xs tracking-wide uppercase">
					External references ({{ entity.external_references.length }})
				</div>
				<div v-for="(reference, index) of entity.external_references" :key="index" class="text-sm">
					<span class="text-secondary">{{ reference.source_name || "source" }}</span>
					<span v-if="reference.external_id" class="text-secondary font-mono">
						· {{ reference.external_id }}
					</span>
					<div v-if="reference.url">
						<a :href="reference.url" target="_blank" rel="noopener noreferrer" class="break-all">
							{{ reference.url }}
						</a>
					</div>
				</div>
			</div>

			<div v-if="objectUrl(entity.id)" class="flex justify-end">
				<a :href="objectUrl(entity.id) || undefined" target="_blank" rel="noopener noreferrer" class="text-sm">
					Open in OpenCTI
				</a>
			</div>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { OpenCTIEntity } from "@/types/opencti"
import axios from "axios"
import { NSpin, NTag } from "naive-ui"
import { ref, watch } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import { useOpenCTIAvailability } from "@/composables/useOpenCTIAvailability"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
// TEMP(mock): UI/UX review — restore `import Api from "@/api"` and `Api.opencti` before merging.
import mockOpenCTI from "./__mock__/opencti-mock"
import { markingType, scoreColor } from "./utils"

const { entityId } = defineProps<{
	/** OpenCTI internal id or STIX standard_id */
	entityId: string
}>()

const dFormats = useSettingsStore().dateFormat
const { objectUrl } = useOpenCTIAvailability()
const loading = ref(false)
const entity = ref<OpenCTIEntity | null>(null)
const error = ref("")

let controller: AbortController | null = null

function load(id: string) {
	controller?.abort()
	const current = new AbortController()
	controller = current
	loading.value = true
	error.value = ""
	entity.value = null

	mockOpenCTI
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
