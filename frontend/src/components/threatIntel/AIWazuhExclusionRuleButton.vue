<template>
	<div>
		<n-button :size="size || 'small'" ghost type="primary" :loading @click="analysis()">
			<template #icon>
				<Icon :name="AiIcon" />
			</template>
			Generate Wazuh Exclusion Rule
		</n-button>

		<n-modal
			v-model:show="showModal"
			preset="card"
			content-class="!p-0"
			:style="{ maxWidth: 'min(710px, 90vw)', minHeight: 'min(500px, 90vh)' }"
			:bordered="false"
			title="Wazuh Exclusion Rule"
			segmented
		>
			<div
				v-if="analysisResponse?.wazuh_exclusion_rule || analysisResponse?.wazuh_exclusion_rule_justification"
				class="flex flex-col gap-7 !p-7"
			>
				<div v-if="analysisResponse?.wazuh_exclusion_rule">
					<CodeSource :code="analysisResponse.wazuh_exclusion_rule" :decode="true" />
				</div>
				<div v-if="analysisResponse?.wazuh_exclusion_rule_justification">
					<Suspense>
						<Markdown :source="analysisResponse.wazuh_exclusion_rule_justification" />
					</Suspense>
				</div>
			</div>
			<n-empty v-else description="No rules found" class="h-48 justify-center" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { AiAnalysisResponse, AiWazuhExclusionRuleResponse } from "@/types/threatIntel.d"
import type { Size } from "naive-ui/es/button/src/interface"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { NButton, NEmpty, NModal, NTabPane, NTabs, useMessage } from "naive-ui"
import { defineAsyncComponent, ref } from "vue"

const { indexName, indexId, size } = defineProps<{
	indexName: string
	indexId: string
	size?: Size
}>()

const CodeSource = defineAsyncComponent(() => import("@/components/common/CodeSource.vue"))
const Markdown = defineAsyncComponent(() => import("@/components/common/Markdown.vue"))

const AiIcon = "mage:stars-c"
const showModal = ref<boolean>(false)
const loading = ref<boolean>(false)
const message = useMessage()
const analysisResponse = ref<AiWazuhExclusionRuleResponse | null>(null)

function openResponse() {
	showModal.value = true
}

function analysis() {
	loading.value = true

	Api.threatIntel
		.aiWazuhExclusionRule({ indexName, indexId })
		.then(res => {
			if (res.data.success) {
				analysisResponse.value = res.data

				if (res.data.wazuh_exclusion_rule) {
					analysisResponse.value.wazuh_exclusion_rule = res.data.wazuh_exclusion_rule.replace(
						/\\\\/g,
						"\\\\\\\\"
					)
				}

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
</script>
