<template>
	<n-spin :show="loading">
		<CardEntity v-if="resolvedGap" :embedded>
			<template #headerMain>
				<div class="flex flex-col gap-1">
					<div class="text-secondary text-xs tracking-wide uppercase">MITRE ATT&amp;CK Gap</div>
					<div class="text-default font-mono text-lg leading-tight font-semibold">
						{{ resolvedGap.technique_id }}
					</div>
				</div>
			</template>

			<template #default>
				<div class="flex flex-col gap-4">
					<p class="text-default text-base leading-snug font-medium">
						{{ resolvedGap.technique_name }}
					</p>

					<div v-if="resolvedGap.tactics.length" class="flex flex-wrap gap-1.5">
						<n-tag v-for="tactic of resolvedGap.tactics" :key="tactic" type="warning" size="small">
							{{ tactic.toUpperCase() }}
						</n-tag>
					</div>
					<p v-else class="text-secondary text-sm">No tactics mapped for this technique.</p>

					<n-button
						v-if="resolvedGap.url"
						tag="a"
						:href="resolvedGap.url"
						target="_blank"
						rel="noopener"
						size="small"
						type="primary"
						secondary
					>
						<template #icon>
							<Icon name="carbon:launch" :size="12" />
						</template>
						View on MITRE ATT&amp;CK
					</n-button>
				</div>
			</template>
		</CardEntity>
	</n-spin>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { CatalogCoverageGapRow } from "@/types/detection-catalog"
import axios from "axios"
import { NButton, NSpin, NTag, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"

const props = withDefaults(
	defineProps<{
		gap?: CatalogCoverageGapRow | null
		techniqueId?: string | null
		embedded?: boolean
	}>(),
	{ embedded: true }
)

const emit = defineEmits<{
	(e: "loaded", value: CatalogCoverageGapRow): void
}>()

const message = useMessage()
const loading = ref(false)
const fetchedGap = ref<CatalogCoverageGapRow | null>(null)

let abortController: AbortController | null = null

const resolvedGap = computed(() => props.gap ?? fetchedGap.value)

function loadGap(techniqueId: string) {
	abortController?.abort()
	abortController = new AbortController()
	loading.value = true

	Api.detectionCatalog
		.getCoverageGap(techniqueId, abortController.signal)
		.then(res => {
			loading.value = false

			if (res.data.success && res.data.gap) {
				fetchedGap.value = res.data.gap
				emit("loaded", res.data.gap)
			} else {
				message.warning(res.data?.message || "Coverage gap not found.")
			}
		})
		.catch(err => {
			if (!axios.isCancel(err)) {
				message.error(getApiErrorMessage(err as ApiError) || "Failed to load coverage gap.")
				loading.value = false
			}
		})
}

watch(
	() => [props.gap, props.techniqueId] as const,
	([gap, techniqueId]) => {
		if (gap) {
			abortController?.abort()
			fetchedGap.value = null
			loading.value = false
			return
		}

		if (techniqueId) {
			loadGap(techniqueId)
			return
		}

		abortController?.abort()
		fetchedGap.value = null
		loading.value = false
	},
	{ immediate: true }
)

defineExpose({ loading, resolvedGap })
</script>
