<template>
	<div>
		<div v-if="badge" class="alert-assets-badge" @click="showDetails = true">
			<code>
				<span>{{ asset.asset_name }}</span>
				<Icon :name="ViewIcon" :size="14" />
			</code>
		</div>
		<CardEntity v-else :embedded hoverable clickable @click="showDetails = true">
			<template #default>{{ asset.asset_name }}</template>
			<template #mainExtra>
				<div class="flex flex-wrap items-center gap-3">
					<Badge type="splitted">
						<template #label>Index</template>
						<template #value>
							<div class="flex h-full items-center">
								<code
									class="text-primary cursor-pointer leading-none"
									@click.stop="gotoIndex(asset.index_name)"
								>
									{{ asset.index_name }}
									<Icon :name="LinkIcon" :size="14" class="relative top-0.5" />
								</code>
							</div>
						</template>
					</Badge>

					<Badge type="splitted">
						<template #label>Agent</template>
						<template #value>
							<div class="flex h-full items-center">
								<code
									class="text-primary cursor-pointer leading-none"
									@click.stop="gotoAgent(asset.agent_id)"
								>
									{{ asset.agent_id }}
									<Icon :name="LinkIcon" :size="14" class="relative top-0.5" />
								</code>
							</div>
						</template>
					</Badge>
				</div>
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			content-class="!p-0"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(550px, 90vh)', overflow: 'hidden' }"
			:bordered="false"
			:title="assetNameTruncated"
			segmented
		>
			<LicenseFeatureCheck
				feature="SOCFORTRESS AI"
				@response="
					(() => {
						licenseChecked = true
						licenseResponse = $event
					})()
				"
			/>
			<n-spin :show="!licenseChecked" content-class="flex flex-wrap justify-end gap-3 p-6" :size="18">
				<AIVelociraptorArtifactRecommendationButton
					:index-id="asset.index_id"
					:index-name="asset.index_name"
					:agent-id="asset.agent_id"
					:alert-id="asset.alert_linked"
					:force-license-response="licenseResponse"
				/>
				<AIWazuhExclusionRuleButton
					:index-id="asset.index_id"
					:index-name="asset.index_name"
					:alert-id="asset.alert_linked"
					:force-license-response="licenseResponse"
				/>
				<AIAnalystButton
					:index-id="asset.index_id"
					:index-name="asset.index_name"
					:alert-id="asset.alert_linked"
					:force-license-response="licenseResponse"
				/>
			</n-spin>

			<n-divider class="!my-0" />

			<n-tabs type="line" animated :tabs-padding="24">
				<n-tab-pane name="Info" tab="Info" display-directive="show">
					<AlertAssetInfo :asset />
				</n-tab-pane>
				<n-tab-pane name="Context" tab="Context" display-directive="show">
					<n-spin :show="loading" class="min-h-40">
						<div v-if="alertContext" class="p-7 pt-4">
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
					<div class="p-7 pt-4">
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
				<n-tab-pane name="Artifact Collection" tab="Artifact Collection" display-directive="show:lazy">
					<div class="p-7 pt-2">
						<ArtifactsCollect
							:hostname="asset.asset_name"
							:artifacts-filter="{ hostname: asset.asset_name }"
							hide-hostname-field
							velociraptor-id="string"
							hide-velociraptor-id-field
						/>
					</div>
				</n-tab-pane>
				<n-tab-pane name="Alert Timeline" tab="Alert Timeline" display-directive="show:lazy">
					<div class="p-7 pt-2">
						<AlertDetailTimeline :asset />
					</div>
				</n-tab-pane>
				<n-tab-pane name="File Collection" tab="File Collection" display-directive="show:lazy">
					<div class="p-7 pt-2">
						<FileCollectionForm v-if="asset.agent_id" :agent-id="asset.agent_id" />

						<n-empty v-else description="No agent associated with this asset" class="h-40" />
					</div>
				</n-tab-pane>
				<n-tab-pane name="Data Store" tab="Data Store" display-directive="show:lazy">
					<div class="p-7 pt-2">
						<AgentDataStoreTabCompact v-if="asset.agent_id" :agent-id="asset.agent_id" />
						<n-empty v-else description="No agent associated with this asset" class="h-40" />
					</div>
				</n-tab-pane>
			</n-tabs>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { AlertAsset, AlertContext } from "@/types/incidentManagement/alerts.d"
import _truncate from "lodash/truncate"
import { NCard, NDivider, NModal, NSpin, NTabPane, NTabs, useMessage } from "naive-ui"
import { computed, defineAsyncComponent, ref, watch } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useGoto } from "@/composables/useGoto"

const { asset, embedded, badge } = defineProps<{ asset: AlertAsset; embedded?: boolean; badge?: boolean }>()

const AlertAssetInfo = defineAsyncComponent(() => import("./AlertAssetInfo.vue"))
const AlertDetailTimeline = defineAsyncComponent(() => import("./AlertDetailTimeline.vue"))
// const ArtifactRecommendation = defineAsyncComponent(() => import("@/components/artifacts/ArtifactRecommendation.vue"))
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
const AgentDataStoreTabCompact = defineAsyncComponent(
	() => import("@/components/agents/dataStore/AgentDataStoreTabCompact.vue")
)
const FileCollectionForm = defineAsyncComponent(
	() => import("@/components/agents/fileCollection/FileCollectionForm.vue")
)

const ViewIcon = "iconoir:eye-solid"
const LinkIcon = "carbon:launch"
const { gotoAgent, gotoIndex } = useGoto()
const message = useMessage()
const loading = ref(false)
const showDetails = ref(false)
const assetNameTruncated = computed(() => _truncate(asset.asset_name, { length: 50 }))
const alertContext = ref<AlertContext | null>(null)
const processNameList = computed<string[]>(() => alertContext.value?.context?.process_name || [])
const isInvestigationAvailable = computed(() => processNameList.value.length)

const licenseChecked = ref(false)
const licenseResponse = ref(false)

watch(showDetails, val => {
	if (val && !alertContext.value) {
		getAlertContext(asset.alert_context_id)
	}
})

function getAlertContext(alertContextId: number) {
	loading.value = true

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
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}
</script>

<style lang="scss" scoped>
.alert-assets-badge {
	color: var(--primary-color);
	line-height: 1;
	cursor: pointer;

	code {
		display: flex;
		align-items: center;
		gap: 7px;
		padding: 2px 5px;
	}
}
</style>
