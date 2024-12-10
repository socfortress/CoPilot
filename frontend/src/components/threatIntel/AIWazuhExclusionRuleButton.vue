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
					<span>Generate Wazuh Exclusion Rule</span>
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
			title="Wazuh Exclusion Rule"
			segmented
		>
			<div
				v-if="analysisResponse?.wazuh_exclusion_rule || analysisResponse?.wazuh_exclusion_rule_justification"
				class="flex flex-col gap-7 p-7"
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
import type { AiWazuhExclusionRuleResponse } from "@/types/threatIntel.d"
import type { Size } from "naive-ui/es/button/src/interface"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import LicenseFeatureCheck from "@/components/license/LicenseFeatureCheck.vue"
import { NButton, NEmpty, NModal, useMessage } from "naive-ui"
import { defineAsyncComponent, ref, watchEffect } from "vue"

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
const analysisResponse = ref<AiWazuhExclusionRuleResponse | null>(null)
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
		.aiWazuhExclusionRule({ indexName, indexId, alertId })
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

watchEffect(() => {
	licenseResponse.value = forceLicenseResponse ?? false
	licenseChecked.value = forceLicenseResponse !== undefined
	disabledLicenseCheck.value = forceLicenseResponse !== undefined
})
</script>
