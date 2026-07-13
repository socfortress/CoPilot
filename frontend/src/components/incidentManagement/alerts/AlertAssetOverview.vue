<template>
	<div class="flex flex-col">
		<LicenseFeatureCheck
			feature="SOCFORTRESS AI"
			@response="
				(() => {
					licenseChecked = true
					licenseResponse = $event
				})()
			"
		/>
		<n-spin
			:show="loadingDetails || !licenseChecked"
			content-class="flex flex-wrap gap-3"
			:class="fullWidth ? 'py-4' : 'px-6 py-4'"
			:size="18"
		>
			<AIVelociraptorArtifactRecommendationButton
				v-if="resolvedAsset"
				:index-id="resolvedAsset.index_id"
				:index-name="resolvedAsset.index_name"
				:agent-id="resolvedAsset.agent_id"
				:alert-id="resolvedAsset.alert_linked"
				:force-license-response="licenseResponse"
			/>
			<AIWazuhExclusionRuleButton
				v-if="resolvedAsset"
				:index-id="resolvedAsset.index_id"
				:index-name="resolvedAsset.index_name"
				:alert-id="resolvedAsset.alert_linked"
				:force-license-response="licenseResponse"
			/>
			<AIAnalystButton
				v-if="resolvedAsset"
				:index-id="resolvedAsset.index_id"
				:index-name="resolvedAsset.index_name"
				:alert-id="resolvedAsset.alert_linked"
				:force-license-response="licenseResponse"
			/>
		</n-spin>

		<n-divider class="my-0!" />

		<n-tabs type="line" animated :tabs-padding="fullWidth ? 0 : 24">
			<n-tab-pane name="Info" tab="Info" display-directive="show">
				<AlertAssetInfo v-if="resolvedAsset" :asset="resolvedAsset" />
			</n-tab-pane>
			<n-tab-pane name="Context" tab="Context" display-directive="show">
				<n-spin :show="loadingContext" class="min-h-40">
					<div v-if="alertContext" :class="fullWidth ? 'pt-3' : 'p-6 pt-3'">
						<div class="mb-4 flex flex-wrap gap-3">
							<Badge type="splitted">
								<template #label>id</template>
								<template #value>#{{ alertContext.id }}</template>
							</Badge>
							<Badge type="splitted">
								<template #label>source</template>
								<template #value>
									{{ alertContext.source }}
								</template>
							</Badge>
						</div>

						<CodeSource :code="alertContext.context" lang="json" />
					</div>
				</n-spin>
			</n-tab-pane>
			<n-tab-pane
				v-if="isInvestigationAvailable"
				name="Investigate"
				tab="Investigate"
				display-directive="show:lazy"
			>
				<div :class="fullWidth ? 'pt-3' : 'p-6 pt-3'">
					<div class="flex flex-wrap gap-2">
						<ThreatIntelProcessEvaluationProvider
							v-for="pn of processNameList"
							:key="pn"
							v-slot="{ openEvaluation }"
							:process-name="pn"
						>
							<n-card
								size="small"
								embedded
								class="hover:border-primary cursor-pointer overflow-hidden"
								@click="openEvaluation()"
							>
								{{ pn }}
							</n-card>
						</ThreatIntelProcessEvaluationProvider>
					</div>
				</div>
			</n-tab-pane>
			<n-tab-pane v-if="isWazuhSource" name="CoPilot Searches" tab="CoPilot Searches" display-directive="show:lazy">
				<div :class="fullWidth ? 'pt-3' : 'p-6 pt-3'">
					<AlertAssetSearches v-if="resolvedAsset" :asset="resolvedAsset" />
				</div>
			</n-tab-pane>
			<n-tab-pane
				v-if="isWazuhSource"
				name="Artifact Collection"
				tab="Artifact Collection"
				display-directive="show:lazy"
			>
				<div :class="fullWidth ? 'pt-2' : 'p-7 pt-2'">
					<ArtifactsCollect
						v-if="resolvedAsset"
						:hostname="resolvedAsset.asset_name"
						:artifacts-filter="{ hostname: resolvedAsset.asset_name }"
						hide-hostname-field
						velociraptor-id="string"
						hide-velociraptor-id-field
					/>
				</div>
			</n-tab-pane>
			<n-tab-pane v-if="isWazuhSource" name="Alert Timeline" tab="Alert Timeline" display-directive="show:lazy">
				<div :class="fullWidth ? 'pt-2' : 'p-7 pt-2'">
					<AlertDetailTimeline v-if="resolvedAsset" :asset="resolvedAsset" />
				</div>
			</n-tab-pane>
			<n-tab-pane v-if="isWazuhSource" name="File Collection" tab="File Collection" display-directive="show:lazy">
				<div :class="fullWidth ? 'pt-2' : 'p-7 pt-2'">
					<FileCollectionForm v-if="resolvedAsset?.agent_id" :agent-id="resolvedAsset.agent_id" />

					<n-empty v-else description="No agent associated with this asset" class="h-40" />
				</div>
			</n-tab-pane>
			<n-tab-pane v-if="isWazuhSource" name="Data Store" tab="Data Store" display-directive="show:lazy">
				<div :class="fullWidth ? 'pt-2' : 'p-7 pt-2'">
					<AgentDataStore v-if="resolvedAsset?.agent_id" :agent-id="resolvedAsset.agent_id" />
					<n-empty v-else description="No agent associated with this asset" class="h-40" />
				</div>
			</n-tab-pane>
		</n-tabs>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { AlertAsset, AlertContext } from "@/types/incidentManagement/alerts"
import { NCard, NDivider, NEmpty, NSpin, NTabPane, NTabs, useMessage } from "naive-ui"
import { computed, defineAsyncComponent, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import { getApiErrorMessage } from "@/utils"

const { asset, alertId, assetId, fullWidth = false } = defineProps<{
	asset?: AlertAsset
	alertId?: number
	assetId?: number
	fullWidth?: boolean
}>()

const emit = defineEmits<{
	(e: "loaded", value: AlertAsset): void
}>()

const AlertAssetInfo = defineAsyncComponent(() => import("./AlertAssetInfo.vue"))
const AlertDetailTimeline = defineAsyncComponent(() => import("./AlertDetailTimeline.vue"))
const AlertAssetSearches = defineAsyncComponent(() => import("@/components/copilotSearches/AlertAssetSearches.vue"))
const AIAnalystButton = defineAsyncComponent(() => import("@/components/threatIntel/AIAnalystButton.vue"))
const AIWazuhExclusionRuleButton = defineAsyncComponent(
	() => import("@/components/threatIntel/AIWazuhExclusionRuleButton.vue")
)
const AIVelociraptorArtifactRecommendationButton = defineAsyncComponent(
	() => import("@/components/threatIntel/AIVelociraptorArtifactRecommendationButton.vue")
)
const ThreatIntelProcessEvaluationProvider = defineAsyncComponent(
	() => import("@/components/threatIntel/ThreatIntelProcessEvaluationProvider.vue")
)
const ArtifactsCollect = defineAsyncComponent(() => import("@/components/artifacts/ArtifactsCollect.vue"))
const CodeSource = defineAsyncComponent(() => import("@/components/common/CodeSource.vue"))
const LicenseFeatureCheck = defineAsyncComponent(() => import("@/components/license/LicenseFeatureCheck.vue"))
const AgentDataStore = defineAsyncComponent(() => import("@/components/agents/dataStore/AgentDataStore.vue"))
const FileCollectionForm = defineAsyncComponent(
	() => import("@/components/agents/fileCollection/FileCollectionForm.vue")
)

const message = useMessage()
const loadingDetails = ref(false)
const loadingContext = ref(false)
const fetchedAsset = ref<AlertAsset | undefined>(undefined)
const alertContext = ref<AlertContext | null>(null)
const licenseChecked = ref(false)
const licenseResponse = ref(false)

const resolvedAsset = computed(() => asset ?? fetchedAsset.value)
const processNameList = computed<string[]>(() => alertContext.value?.context?.process_name || [])
const isInvestigationAvailable = computed(() => processNameList.value.length)
const isWazuhSource = computed(() => alertContext.value?.source?.toLowerCase() === "wazuh")

watch(
	() => resolvedAsset.value?.alert_context_id,
	alertContextId => {
		if (alertContextId != null && !alertContext.value) {
			getAlertContext(alertContextId)
		}
	},
	{ immediate: true }
)

function getAlertContext(alertContextId: number) {
	loadingContext.value = true

	Api.incidentManagement.alerts
		.getAlertContext(alertContextId)
		.then(res => {
			if (res.data.success) {
				alertContext.value = res.data?.alert_context || null
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingContext.value = false
		})
}

function getDetails(parentAlertId: number, targetAssetId: number) {
	loadingDetails.value = true

	Api.incidentManagement.alerts
		.getAlert(parentAlertId)
		.then(res => {
			if (res.data.success) {
				const match = res.data.alerts?.[0]?.assets?.find(item => item.id === targetAssetId)
				if (match) {
					fetchedAsset.value = match
					emit("loaded", match)
				} else {
					message.warning("Asset not found")
				}
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingDetails.value = false
		})
}

onBeforeMount(() => {
	if (asset) return
	if (alertId != null && assetId != null) getDetails(alertId, assetId)
})
</script>
