<template>
	<div>
		<n-button :size="size || 'small'" ghost type="primary" :loading @click="openAiAnalyst()">
			<template #icon>
				<Icon :name="AiIcon" />
			</template>
			AI Analyst
		</n-button>

		<n-modal
			v-model:show="showModal"
			preset="card"
			content-class="!p-0"
			:style="{ maxWidth: 'min(700px, 90vw)', minHeight: 'min(500px, 90vh)' }"
			:bordered="false"
			segmented
		>
			<template #header>AI Analysis</template>
			<template v-if="analysisResponse" #header-extra>
				<code class="px-2 py-1">CONFIDENCE SCORE: {{ analysisResponse.confidence_score * 100 }}%</code>
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
						<div v-shiki="{ fallbackLang: 'bash', decode: true }" class="scrollbar-styled">
							<pre>{{ analysisResponse.base64_decoded }}</pre>
						</div>
					</div>
				</n-tab-pane>
				<n-tab-pane
					v-if="analysisResponse?.threat_indicators"
					name="ThreatIndicators"
					tab="Threat Indicators"
					display-directive="show"
				>
					<div class="p-7 pt-4">
						<div v-shiki="{ fallbackLang: 'bash', decode: true }" class="scrollbar-styled">
							<pre>{{ analysisResponse.threat_indicators }}</pre>
						</div>
					</div>
				</n-tab-pane>
				<n-tab-pane
					v-if="analysisResponse?.risk_evaluation"
					name="RiskEvaluation"
					tab="Risk Evaluation"
					display-directive="show"
				>
					<div class="p-7 pt-4">
						<div v-shiki="{ fallbackLang: 'bash', decode: true }" class="scrollbar-styled">
							<pre>{{ analysisResponse.risk_evaluation }}</pre>
						</div>
					</div>
				</n-tab-pane>
				<n-tab-pane
					v-if="
						analysisResponse?.wazuh_exclusion_rule || analysisResponse?.wazuh_exclusion_rule_justification
					"
					name="WazuhExclusionRule"
					tab="Wazuh Exclusion Rule"
					display-directive="show"
					class="flex flex-col gap-7 !p-7"
				>
					<div v-if="analysisResponse?.wazuh_exclusion_rule">
						<div v-shiki="{ fallbackLang: 'bash', decode: true }" class="scrollbar-styled">
							<pre>{{ analysisResponse.wazuh_exclusion_rule }}</pre>
						</div>
					</div>
					<div v-if="analysisResponse?.wazuh_exclusion_rule_justification">
						<Suspense>
							<Markdown :source="analysisResponse.wazuh_exclusion_rule_justification" />
						</Suspense>
					</div>
				</n-tab-pane>
			</n-tabs>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { AiAnalysisResponse } from "@/types/threatIntel.d"
import type { Size } from "naive-ui/es/button/src/interface"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import vShiki from "@/directives/v-shiki"
import { NButton, NModal, NTabPane, NTabs, useMessage } from "naive-ui"
import { defineAsyncComponent, ref } from "vue"

const { indexName, indexId, size } = defineProps<{
	indexName: string
	indexId: string
	size?: Size
}>()

const Markdown = defineAsyncComponent(() => import("@/components/common/Markdown.vue"))

const AiIcon = "mage:stars-c"
const showModal = ref<boolean>(false)
const loading = ref<boolean>(false)
const message = useMessage()
const analysisResponse = ref<AiAnalysisResponse | null>(null)

function openAiAnalysis() {
	showModal.value = true
}

function openAiAnalyst() {
	loading.value = true

	Api.threatIntel
		.aiAlertAnalysis({ indexName, indexId })
		.then(res => {
			if (res.data.success) {
				analysisResponse.value = res.data

				openAiAnalysis()
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
</script>
