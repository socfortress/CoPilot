<template>
	<n-spin :show="loadingDetails" content-class="min-h-40">
		<div v-if="tacticDetails" class="flex flex-col gap-4 md:flex-row">
			<div class="flex grow flex-col gap-3">
				<code class="self-start">
					{{ tacticDetails.id ?? "—" }}
				</code>

				<CardKV>
					<template #key>name</template>
					<template #value>
						<span class="whitespace-pre-wrap">
							{{ tacticDetails.name ?? "—" }}
						</span>
					</template>
				</CardKV>
				<CardKV v-if="tacticDetails.description" class="[&_p]:text-white">
					<template #key>description</template>
					<template #value>
						<Suspense>
							<Markdown :source="tacticDetails.description" />
						</Suspense>
					</template>
				</CardKV>

				<CardKV v-if="tacticDetails.references?.length">
					<template #key>references</template>
					<template #value>
						<References :references="tacticDetails.references" />
					</template>
				</CardKV>
			</div>
			<div ref="sidebarRef" class="md:max-w-70 shrink-0 basis-1/3">
				<div ref="sidebarCardRef" class="flex flex-col gap-2 will-change-transform">
					<n-card content-class="bg-secondary flex flex-col gap-3 rounded-lg" size="small">
						<div class="flex flex-col gap-0.5 text-sm">
							<div class="text-secondary font-mono text-xs">external_id</div>
							<div>{{ tacticDetails.external_id }}</div>
						</div>
						<div class="flex flex-col gap-0.5 text-sm">
							<div class="text-secondary font-mono text-xs">short_name</div>
							<div>{{ tacticDetails.short_name }}</div>
						</div>
						<div class="flex flex-col gap-0.5 text-sm">
							<div class="text-secondary font-mono text-xs">created_time</div>
							<div>{{ formatDate(tacticDetails.created_time, dFormats.datetime) }}</div>
						</div>
						<div class="flex flex-col gap-0.5 text-sm">
							<div class="text-secondary font-mono text-xs">modified_time</div>
							<div>{{ formatDate(tacticDetails.modified_time, dFormats.datetime) }}</div>
						</div>
						<div class="flex flex-col gap-0.5 text-sm">
							<div class="text-secondary font-mono text-xs">url</div>
							<div>
								<a :href="tacticDetails.url" target="_blank" rel="nofollow noopener noreferrer">
									{{ tacticDetails.url }}
								</a>
							</div>
						</div>
						<div class="flex flex-col gap-0.5 text-sm">
							<div class="text-secondary font-mono text-xs">source</div>
							<div>{{ tacticDetails.source }}</div>
						</div>
					</n-card>
				</div>
			</div>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { MitreTacticDetails } from "@/types/mitre.d"
import { useElementBounding, useRafFn } from "@vueuse/core"
import { useMotionProperties } from "@vueuse/motion"
import { NCard, NSpin, useMessage } from "naive-ui"
import { defineAsyncComponent, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import CardKV from "@/components/common/cards/CardKV.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import References from "../common/References.vue"

const { externalId, entity } = defineProps<{
	externalId?: string
	entity?: MitreTacticDetails
}>()

const Markdown = defineAsyncComponent(() => import("@/components/common/Markdown.vue"))

const dFormats = useSettingsStore().dateFormat
const message = useMessage()
const loadingDetails = ref(false)
const tacticDetails = ref<MitreTacticDetails | null>(null)

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

function getDetails(id: string) {
	loadingDetails.value = true

	Api.wazuh.mitre
		.getMitreTactics({ id })
		.then(res => {
			if (res.data.success) {
				tacticDetails.value = res.data.results?.[0] || null
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
		getDetails(externalId)
	}
	if (entity) {
		tacticDetails.value = entity
	}
})
</script>
