<template>
	<div>
		<LicenseFeatureCheck
			feature="SOCFORTRESS AI"
			feedback="tooltip"
			:disabled="disabledLicenseCheck"
			:force-show-feedback="disabledLicenseCheck && !licenseResponse"
			@response="
				(() => {
					licenseChecked = true
					licenseResponse = $event
				})()
			"
			@start-loading="licenseChecking = true"
			@stop-loading="licenseChecking = false"
		>
			<n-button
				:size="size || 'small'"
				ghost
				type="primary"
				:loading="loading || licenseChecking"
				:disabled="!licenseChecked || !licenseResponse"
				@click="analysis()"
			>
				<template #icon>
					<Icon :name="AiIcon" />
				</template>
				<div class="flex items-center gap-2">
					<span>Velociraptor Artifact Recommendation</span>
					<Icon v-if="!licenseResponse && licenseChecked" :name="LockIcon" :size="14" />
				</div>
			</n-button>
		</LicenseFeatureCheck>

		<n-modal
			v-model:show="showModal"
			preset="card"
			content-class="!p-0"
			:style="{ maxWidth: 'min(710px, 90vw)', minHeight: 'min(500px, 90vh)' }"
			:bordered="false"
			title="Velociraptor Artifact Recommendation"
			segmented
		>
			<div v-if="analysisResponse?.general_thoughts" class="p-6 pb-3">
				{{ analysisResponse.general_thoughts }}
			</div>
			<div v-if="analysisResponse?.artifact_recommendations?.length" class="flex flex-col gap-3 p-6">
				<CardEntity
					v-for="recommendation of analysisResponse.artifact_recommendations"
					:key="recommendation.name + recommendation.explanation + recommendation.description"
					embedded
				>
					<template #header>
						{{ recommendation.name }}
					</template>
					<template #default>
						{{ recommendation.description }}
					</template>
					<template #footer>
						{{ recommendation.explanation }}
					</template>
				</CardEntity>
			</div>
			<n-empty v-else description="No Recommendations found" class="h-48 justify-center" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { AiVelociraptorArtifactRecommendationResponse } from "@/types/threatIntel.d"
import type { Size } from "naive-ui/es/button/src/interface"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import LicenseFeatureCheck from "@/components/license/LicenseFeatureCheck.vue"
import { NButton, NEmpty, NModal, useMessage } from "naive-ui"
import { ref, watchEffect } from "vue"

const {
	indexName,
	indexId,
	agentId,
	alertId,
	forceLicenseResponse = undefined,
	size
} = defineProps<{
	indexName: string
	indexId: string
	agentId: string
	alertId: number
	forceLicenseResponse?: boolean
	size?: Size
}>()

const LockIcon = "carbon:locked"
const AiIcon = "mage:stars-c"
const showModal = ref<boolean>(false)
const loading = ref<boolean>(false)
const message = useMessage()
const analysisResponse = ref<AiVelociraptorArtifactRecommendationResponse | null>(null)
const licenseChecking = ref(false)
const licenseChecked = ref(forceLicenseResponse !== undefined)
const licenseResponse = ref(forceLicenseResponse ?? false)
const disabledLicenseCheck = ref(forceLicenseResponse !== undefined)

function openResponse() {
	showModal.value = true
}

function analysis() {
	loading.value = true

	Api.threatIntel
		.aiVelociraptorArtifactRecommendation({ indexName, indexId, agentId, alertId })
		.then(res => {
			if (res.data.success) {
				analysisResponse.value = res.data

				openResponse()
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

watchEffect(() => {
	licenseResponse.value = forceLicenseResponse ?? false
	licenseChecked.value = forceLicenseResponse !== undefined
	disabledLicenseCheck.value = forceLicenseResponse !== undefined
})
</script>
