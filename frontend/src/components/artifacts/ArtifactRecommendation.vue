<template>
	<div>
		<n-button :size="size || 'small'" ghost type="primary" @click="openRecommendations()">
			<template #icon>
				<Icon :name="AiIcon" />
			</template>
			Recommend Artifact Collection
		</n-button>

		<n-modal
			v-model:show="showModal"
			preset="card"
			:style="{ maxWidth: 'min(700px, 90vw)', minHeight: 'min(500px, 90vh)' }"
			title="Recommend Artifact Collection"
			:bordered="false"
			display-directive="show"
			segmented
		>
			<div class="mb-4 flex flex-wrap items-center gap-3">
				<div>Get Recommendations for OS:</div>
				<n-select
					v-model:value="selectedOs"
					size="small"
					:options="osOptions"
					class="!w-32"
					placeholder="Select OS"
					:disabled="loading"
				/>
				<n-button
					v-if="!recommendations.length"
					size="small"
					type="primary"
					:loading
					:disabled="!selectedOs"
					@click="getRecommendations()"
				>
					<template #icon>
						<Icon :name="AiIcon" />
					</template>
					Submit
				</n-button>
			</div>
			<n-spin :show="loading" class="min-h-48">
				<div v-if="recommendations.length" class="flex flex-col gap-2">
					<n-card
						v-for="recommendation of recommendations"
						:key="recommendation.name"
						embedded
						content-class="flex flex-col gap-2 !p-0"
						class="item-appear item-appear-bottom item-appear-005 overflow-hidden"
						size="small"
					>
						<strong class="recommendation-name px-4 pt-3 pb-1 font-mono">{{ recommendation.name }}</strong>
						<n-divider class="!m-0" />
						<div class="recommendation-description px-4 pt-1">
							{{ recommendation.description }}
						</div>
						<p class="recommendation-explanation px-4 pt-2 pb-3">
							{{ recommendation.explanation }}
						</p>
					</n-card>
				</div>
				<n-empty
					v-if="!loading && !recommendations.length"
					description="Recommendations not found"
					class="h-48 justify-center"
				/>
			</n-spin>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { Size } from "naive-ui/es/button/src/interface"
import type { Recommendation } from "@/types/artifacts.d"
import type { OsTypesFull } from "@/types/common.d"
import _uniqBy from "lodash/uniqBy"
import { NButton, NCard, NDivider, NEmpty, NModal, NSelect, NSpin, useMessage } from "naive-ui"
import { computed, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"

interface RecommendationStore {
	os: OsTypesFull
	recommendation: Recommendation[]
}

const { context, size } = defineProps<{
	context: string | object
	size?: Size
}>()

const AiIcon = "mage:stars-c"
const showModal = ref<boolean>(false)
const loading = ref<boolean>(false)
const message = useMessage()

const recommendationsStore = ref<RecommendationStore[]>([])
const selectedOs = ref<OsTypesFull | null>(null)
const recommendations = computed<Recommendation[]>(
	() => recommendationsStore.value.find(item => item.os === selectedOs.value)?.recommendation || []
)

const osOptions: { label: string; value: OsTypesFull }[] = [
	{ label: "Windows", value: "Windows" },
	{ label: "Linux", value: "Linux" },
	{ label: "MacOS", value: "MacOS" }
]

function openRecommendations() {
	showModal.value = true
}

function getRecommendations() {
	if (selectedOs.value !== null && context) {
		loading.value = true

		const requestedOs = selectedOs.value

		Api.artifacts
			.getArtifactRecommendation({ os: requestedOs, prompt: context })
			.then(res => {
				if (res.data.success) {
					recommendationsStore.value.push({
						os: requestedOs,
						recommendation: res.data?.recommendations || []
					})
					recommendationsStore.value = _uniqBy(recommendationsStore.value, "os")
				} else {
					message.warning(res.data?.message || "An error occurred. Please try again later.")
				}
			})
			.catch(err => {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			})
			.finally(() => {
				loading.value = false
			})
	}
}
</script>
