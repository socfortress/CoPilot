<template>
	<div v-if="techniqueDetails" class="flex flex-col gap-4 md:flex-row">
		<div class="flex grow flex-col gap-3">
			<code class="self-start">
				{{ techniqueDetails.id ?? "-" }}
			</code>

			<CardKV>
				<template #key>name</template>
				<template #value>
					<span class="whitespace-pre-wrap">
						{{ techniqueDetails.name ?? "-" }}
					</span>
				</template>
			</CardKV>
			<CardKV>
				<template #key>description</template>
				<template #value>
					<span class="whitespace-pre-wrap">
						{{ techniqueDetails.description ?? "-" }}
					</span>
				</template>
			</CardKV>
			<CardKV>
				<template #key>mitre_detection (v{{ techniqueDetails.mitre_version }})</template>
				<template #value>
					<span class="whitespace-pre-wrap">
						{{ techniqueDetails.mitre_detection ?? "-" }}
					</span>
				</template>
			</CardKV>
			<CardKV>
				<template #key>references</template>
				<template #value>
					<div class="divide-border flex flex-col gap-4 divide-y-2">
						<div
							v-for="reference of techniqueDetails.references"
							:key="reference.url"
							class="flex flex-col gap-0.5 pb-1 text-sm"
						>
							<div>{{ reference.source }}</div>
							<div class="text-secondary text-xs">{{ reference.description }}</div>
							<div>
								<a :href="reference.url" target="_blank" rel="nofollow noopener noreferrer">
									{{ reference.url }}
								</a>
							</div>
						</div>
					</div>
				</template>
			</CardKV>
		</div>
		<div class="md:max-w-70 shrink-0 basis-1/3">
			<n-card content-class="bg-secondary flex flex-col gap-3 rounded-lg" size="small">
				<div class="flex flex-col gap-0.5 text-sm">
					<div class="text-secondary font-mono text-xs">external_id</div>
					<div>{{ techniqueDetails.external_id }}</div>
				</div>
				<div class="flex flex-col gap-0.5 text-sm">
					<div class="text-secondary font-mono text-xs">created_time</div>
					<div>{{ formatDate(techniqueDetails.created_time, dFormats.datetime) }}</div>
				</div>
				<div class="flex flex-col gap-0.5 text-sm">
					<div class="text-secondary font-mono text-xs">modified_time</div>
					<div>{{ formatDate(techniqueDetails.modified_time, dFormats.datetime) }}</div>
				</div>
				<div class="flex flex-col gap-0.5 text-sm">
					<div class="text-secondary font-mono text-xs">url</div>
					<div>
						<a :href="techniqueDetails.url" target="_blank" rel="nofollow noopener noreferrer">
							{{ techniqueDetails.url }}
						</a>
					</div>
				</div>
				<div class="flex flex-col gap-0.5 text-sm">
					<div class="text-secondary font-mono text-xs">source</div>
					<div>{{ techniqueDetails.source }}</div>
				</div>
				<div v-if="techniqueDetails.subtechnique_of" class="flex flex-col gap-0.5 text-sm">
					<div class="text-secondary font-mono text-xs">subtechnique_of</div>
					<div>{{ techniqueDetails.subtechnique_of }}</div>
				</div>
				<div class="flex flex-col gap-0.5 text-sm">
					<div class="text-secondary font-mono text-xs">platforms</div>
					<div class="mt-0.5 flex flex-wrap gap-1">
						<template v-if="!techniqueDetails.platforms?.length">—</template>
						<template v-else>
							<code v-for="item of techniqueDetails.platforms" :key="item" class="text-xs">
								{{ item }}
							</code>
						</template>
					</div>
				</div>
				<div class="flex flex-col gap-0.5 text-sm">
					<div class="text-secondary font-mono text-xs">data_sources</div>
					<div class="mt-0.5 flex flex-wrap gap-1">
						<template v-if="!techniqueDetails.data_sources?.length">—</template>
						<template v-else>
							<code v-for="item of techniqueDetails.data_sources" :key="item" class="text-xs">
								{{ item }}
							</code>
						</template>
					</div>
				</div>
			</n-card>

			<div class="mt-2 flex flex-wrap gap-1">
				<Badge v-if="techniqueDetails.deprecated" color="primary" class="text-xs! font-mono">
					<template #value>deprecated</template>
				</Badge>
				<Badge v-if="techniqueDetails.remote_support" color="primary">
					<template #value>remote_support</template>
				</Badge>
				<Badge v-if="techniqueDetails.network_requirements" color="primary">
					<template #value>network_requirements</template>
				</Badge>
				<Badge v-if="techniqueDetails.is_subtechnique" color="primary">
					<template #value>subtechnique</template>
				</Badge>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { MitreTechniqueDetails } from "@/types/mitre.d"
import { NCard, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import { techniqueResultDetails } from "./mock"

const { externalId } = defineProps<{
	externalId: string
}>()

const dFormats = useSettingsStore().dateFormat
const message = useMessage()
const loadingDetails = ref(false)
const techniqueDetails = ref<MitreTechniqueDetails | null>(null)

function getDetails() {
	loadingDetails.value = true

	Api.mitre
		.getMitreTechniqueDetails({ external_id: externalId })
		.then(res => {
			if (res.data.success) {
				techniqueDetails.value = res.data.results?.[0] || null
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingDetails.value = false
		})
}

onBeforeMount(() => {
	/*
	getDetails()
	*/
	// MOCK
	techniqueDetails.value = techniqueResultDetails
})
</script>
