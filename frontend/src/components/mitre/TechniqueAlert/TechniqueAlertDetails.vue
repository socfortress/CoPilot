<template>
	<n-spin :show="loadingDetails" content-class="min-h-40">
		<div v-if="techniqueDetails" class="flex flex-col gap-4 md:flex-row">
			<div class="flex grow flex-col gap-3">
				<code class="self-start">
					{{ techniqueDetails.id ?? "—" }}
				</code>

				<CardKV>
					<template #key>name</template>
					<template #value>
						<span class="whitespace-pre-wrap">
							{{ techniqueDetails.name ?? "—" }}
						</span>
					</template>
				</CardKV>
				<CardKV v-if="techniqueDetails.description" class="[&_p]:text-white">
					<template #key>description</template>
					<template #value>
						<Suspense>
							<Markdown :source="techniqueDetails.description" />
						</Suspense>
					</template>
				</CardKV>
				<CardKV>
					<template #key>mitre_detection (v{{ techniqueDetails.mitre_version }})</template>
					<template #value>
						<span class="whitespace-pre-wrap">
							{{ techniqueDetails.mitre_detection ?? "—" }}
						</span>
					</template>
				</CardKV>
				<CardKV v-if="techniqueDetails.references?.length">
					<template #key>references</template>
					<template #value>
						<References :references="techniqueDetails.references" />
					</template>
				</CardKV>
			</div>
			<div ref="sidebarRef" class="md:max-w-70 shrink-0 basis-1/3">
				<div ref="sidebarCardRef" class="flex flex-col gap-2 will-change-transform">
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

					<div class="flex flex-wrap gap-1">
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
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { MitreTechniqueDetails } from "@/types/mitre.d"
import { useElementBounding, useRafFn } from "@vueuse/core"
import { useMotionProperties } from "@vueuse/motion"
import { NCard, NSpin, useMessage } from "naive-ui"
import { defineAsyncComponent, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import References from "../common/References.vue"

const { externalId, id, entity } = defineProps<{
	externalId?: string
	id?: string
	entity?: MitreTechniqueDetails
}>()

const Markdown = defineAsyncComponent(() => import("@/components/common/Markdown.vue"))

const dFormats = useSettingsStore().dateFormat
const message = useMessage()
const loadingDetails = ref(false)
const techniqueDetails = ref<MitreTechniqueDetails | null>(null)

const sidebarRef = ref(null)
const sidebarCardRef = ref(null)
const { top: sidebarTop } = useElementBounding(sidebarRef)
const { transform: styleCardTransform } = useMotionProperties(sidebarCardRef)

const { resume } = useRafFn(
	() => {
		const targetY = sidebarTop.value <= 50 ? sidebarTop.value * -1 + 50 : 0
		styleCardTransform.translateY = `${targetY}px`
	},
	{ immediate: false }
)

watch(sidebarTop, () => {
	resume()
})

function getDetails(query: { external_id: string } | { id: string }) {
	loadingDetails.value = true

	Api.wazuh.mitre
		.getMitreTechniques(query)
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
	if (externalId) {
		getDetails({ external_id: externalId })
	}
	if (id) {
		getDetails({ id })
	}
	if (entity) {
		techniqueDetails.value = entity
	}
})
</script>
