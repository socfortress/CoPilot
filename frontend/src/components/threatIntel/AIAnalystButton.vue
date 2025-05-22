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
					<span>AI Analyst</span>
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
			segmented
		>
			<template #header>
				<div class="flex flex-wrap items-center gap-2">
					<span>AI Analysis</span>
					<code v-if="analysisResponse?.risk_evaluation" class="px-2 py-1">
						RISK:
						<strong
							:class="{
								'text-warning': analysisResponse?.risk_evaluation === 'medium',
								'text-error': analysisResponse?.risk_evaluation === 'high'
							}"
						>
							{{ analysisResponse.risk_evaluation }}
						</strong>
					</code>
				</div>
			</template>
			<template v-if="analysisResponse" #header-extra>
				<code class="px-2 py-1">
					CONFIDENCE SCORE:
					<strong>{{ analysisResponse.confidence_score * 100 }}%</strong>
				</code>
			</template>
			<n-tabs type="line" animated :tabs-padding="24">
				<n-tab-pane v-if="analysisResponse?.analysis" name="Analysis" tab="Analysis" display-directive="show">
					<div class="p-7 pt-4">
						<Suspense>
							<Markdown :source="analysisResponse.analysis" />
						</Suspense>
					</div>
				</n-tab-pane>
				<n-tab-pane
					v-if="analysisResponse?.base64_decoded"
					name="Base64Decoded"
					tab="Base64 Decoded"
					display-directive="show"
				>
					<div class="p-7 pt-4">
						<CodeSource :code="analysisResponse.base64_decoded" :decode="true" />
					</div>
				</n-tab-pane>
				<n-tab-pane
					v-if="analysisResponse?.threat_indicators"
					name="ThreatIndicators"
					tab="Threat Indicators"
					display-directive="show"
				>
					<div class="p-7 pt-4">
						<Suspense>
							<Markdown :source="analysisResponse.threat_indicators" />
						</Suspense>
					</div>
				</n-tab-pane>
			</n-tabs>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { Size } from "naive-ui/es/button/src/interface"
import type { AiAnalysisResponse } from "@/types/threatIntel.d"
import { NButton, NModal, NTabPane, NTabs, useMessage } from "naive-ui"
import { defineAsyncComponent, ref, watchEffect } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import LicenseFeatureCheck from "@/components/license/LicenseFeatureCheck.vue"

const {
	indexName,
	indexId,
	alertId,
	forceLicenseResponse = undefined,
	size
} = defineProps<{
	indexName: string
	indexId: string
	alertId: number
	forceLicenseResponse?: boolean
	size?: Size
}>()

const CodeSource = defineAsyncComponent(() => import("@/components/common/CodeSource.vue"))
const Markdown = defineAsyncComponent(() => import("@/components/common/Markdown.vue"))

const LockIcon = "carbon:locked"
const AiIcon = "mage:stars-c"
const showModal = ref<boolean>(false)
const loading = ref<boolean>(false)
const message = useMessage()
const analysisResponse = ref<AiAnalysisResponse | null>(null)
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
		.aiAlertAnalysis({ indexName, indexId, alertId })
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
