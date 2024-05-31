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
			<div class="flex gap-3 items-center flex-wrap mb-4">
				<div>Get Recommendations for OS:</div>
				<n-select
					size="small"
					v-model:value="selectedOs"
					:options="osOptions"
					class="!w-32"
					placeholder="Select OS"
				/>
				<n-button
					size="small"
					type="primary"
					:loading
					@click="getRecommendations()"
					:disabled="!selectedOs"
					v-if="!recommendations.length"
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
						content-class="bg-secondary-color flex flex-col gap-2 !p-0"
						class="overflow-hidden item-appear item-appear-bottom item-appear-005"
						v-for="recommendation of recommendations"
						:key="recommendation.name"
						size="small"
					>
						<strong class="recommendation-name font-mono px-4 pt-3 pb-1">{{ recommendation.name }}</strong>
						<n-divider class="!m-0" />
						<div class="recommendation-description px-4 pt-1">{{ recommendation.description }}</div>
						<p class="recommendation-explanation px-4 pb-3 pt-2">{{ recommendation.explanation }}</p>
					</n-card>
				</div>
				<n-empty
					description="Recommendations not found"
					class="justify-center h-48"
					v-if="!loading && !recommendations.length"
				/>
			</n-spin>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import { useMessage, NModal, NSpin, NEmpty, NButton, NDivider, NSelect, NCard } from "naive-ui"
import type { Size } from "naive-ui/es/button/src/interface"
import { computed, ref } from "vue"
import Api from "@/api"
import _uniqBy from "lodash/uniqBy"
import type { SocAlert } from "@/types/soc/alert"
import type { OsTypesFull } from "@/types/common"
import type { Recommendation } from "@/types/artifacts"

interface RecommendationStore {
	os: OsTypesFull
	recommendation: Recommendation[]
}

const { alert, size } = defineProps<{
	alert: SocAlert
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
	if (selectedOs.value !== null && alert) {
		loading.value = true

		const requestedOs = selectedOs.value

		Api.artifacts
			.getArtifactRecommendation({ os: requestedOs, prompt: alert.alert_context })
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
