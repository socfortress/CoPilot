<template>
	<n-spin :show="loadingDetails" content-class="min-h-40">
		<div v-if="softwareDetails" class="flex flex-col gap-4 md:flex-row">
			<div class="flex grow flex-col gap-3">
				<code class="self-start">
					{{ softwareDetails.id ?? "—" }}
				</code>

				<CardKV>
					<template #key>name</template>
					<template #value>
						<span class="whitespace-pre-wrap">
							{{ softwareDetails.name ?? "—" }}
						</span>
					</template>
				</CardKV>
				<CardKV v-if="softwareDetails.description" class="[&_p]:text-white">
					<template #key>description</template>
					<template #value>
						<Markdown :source="softwareDetails.description" />
					</template>
				</CardKV>

				<CardKV v-if="softwareDetails.references?.length">
					<template #key>references</template>
					<template #value>
						<References :references="softwareDetails.references" />
					</template>
				</CardKV>
			</div>
			<div ref="sidebarRef" class="shrink-0 basis-1/3 md:max-w-70">
				<div ref="sidebarCardRef" class="flex flex-col gap-2 will-change-transform">
					<n-card content-class="bg-secondary flex flex-col gap-3 rounded-lg" size="small">
						<div class="flex flex-col gap-0.5 text-sm">
							<div class="text-secondary font-mono text-xs">external_id</div>
							<div>{{ softwareDetails.external_id }}</div>
						</div>
						<div class="flex flex-col gap-0.5 text-sm">
							<div class="text-secondary font-mono text-xs">created_time</div>
							<div>{{ formatDate(softwareDetails.created_time, dFormats.datetime) }}</div>
						</div>
						<div class="flex flex-col gap-0.5 text-sm">
							<div class="text-secondary font-mono text-xs">modified_time</div>
							<div>{{ formatDate(softwareDetails.modified_time, dFormats.datetime) }}</div>
						</div>
						<div class="flex flex-col gap-0.5 text-sm">
							<div class="text-secondary font-mono text-xs">url</div>
							<div>
								<a :href="softwareDetails.url" target="_blank" rel="nofollow noopener noreferrer">
									{{ softwareDetails.url }}
								</a>
							</div>
						</div>
						<div class="flex flex-col gap-0.5 text-sm">
							<div class="text-secondary font-mono text-xs">source</div>
							<div>{{ softwareDetails.source }}</div>
						</div>
						<div class="flex flex-col gap-0.5 text-sm">
							<div class="text-secondary font-mono text-xs">type</div>
							<div>{{ softwareDetails.type || "—" }}</div>
						</div>
						<div class="flex flex-col gap-0.5 text-sm">
							<div class="text-secondary font-mono text-xs">mitre_version</div>
							<div>{{ softwareDetails.mitre_version }}</div>
						</div>
						<div class="flex flex-col gap-0.5 text-sm">
							<div class="text-secondary font-mono text-xs">platforms</div>
							<div class="mt-0.5 flex flex-wrap gap-1">
								<template v-if="!softwareDetails.platforms?.length">—</template>
								<template v-else>
									<code v-for="item of softwareDetails.platforms" :key="item" class="text-xs">
										{{ item }}
									</code>
								</template>
							</div>
						</div>
						<div class="flex flex-col gap-0.5 text-sm">
							<div class="text-secondary font-mono text-xs">aliases</div>
							<div class="mt-0.5 flex flex-wrap gap-1">
								<template v-if="!softwareDetails.aliases?.length">—</template>
								<template v-else>
									<code v-for="item of softwareDetails.aliases" :key="item" class="text-xs">
										{{ item }}
									</code>
								</template>
							</div>
						</div>
					</n-card>

					<div class="flex flex-wrap gap-1">
						<Badge v-if="softwareDetails.deprecated" color="primary" class="font-mono text-xs!">
							<template #value>deprecated</template>
						</Badge>
					</div>
				</div>
			</div>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { MitreSoftwareDetails } from "@/types/mitre.d"
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

const { externalId, entity } = defineProps<{
	externalId?: string
	entity?: MitreSoftwareDetails
}>()

const Markdown = defineAsyncComponent(() => import("@/components/common/Markdown.vue"))

const dFormats = useSettingsStore().dateFormat
const message = useMessage()
const loadingDetails = ref(false)
const softwareDetails = ref<MitreSoftwareDetails | null>(null)

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
		.getMitreSoftware({ id })
		.then(res => {
			if (res.data.success) {
				softwareDetails.value = res.data.results?.[0] || null
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
		softwareDetails.value = entity
	}
})
</script>
