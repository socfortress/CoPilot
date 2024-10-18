<template>
	<div class="alert-asset-item" :class="{ embedded, badge }">
		<code v-if="badge" @click="showDetails = true">
			<span>{{ asset.asset_name }}</span>
			<Icon :name="ViewIcon" :size="14" />
		</code>

		<div v-else class="flex cursor-pointer flex-col" @click="showDetails = true">
			<div class="main-box flex flex-col gap-3 px-5 py-3">
				<div class="content flex grow flex-col gap-1">
					<div class="title">
						{{ asset.asset_name }}
					</div>
				</div>

				<div class="badges-box flex flex-wrap items-center gap-3">
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
			</div>
		</div>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			content-class="!p-0"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(550px, 90vh)', overflow: 'hidden' }"
			:bordered="false"
			segmented
		>
			<template #header>
				<div class="min-h-8">
					{{ assetNameTruncated }}
				</div>
			</template>
			<template #header-extra>
				<div class="min-h-8">
					<ArtifactRecommendation v-if="alertContext" :context="alertContext.context" />
				</div>
			</template>
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
									content-class="bg-secondary"
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
			</n-tabs>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { AlertAsset, AlertContext } from "@/types/incidentManagement/alerts.d"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import Icon from "@/components/common/Icon.vue"
import { useGoto } from "@/composables/useGoto"
import _truncate from "lodash/truncate"
import { NCard, NModal, NSpin, NTabPane, NTabs, useMessage } from "naive-ui"
import { computed, defineAsyncComponent, ref, watch } from "vue"

const { asset, embedded, badge } = defineProps<{ asset: AlertAsset; embedded?: boolean; badge?: boolean }>()

const AlertAssetInfo = defineAsyncComponent(() => import("./AlertAssetInfo.vue"))
const AlertDetailTimeline = defineAsyncComponent(() => import("./AlertDetailTimeline.vue"))
const ArtifactRecommendation = defineAsyncComponent(() => import("@/components/artifacts/ArtifactRecommendation.vue"))
const ThreatIntelProcessEvaluationProvider = defineAsyncComponent(
	() => import("@/components/threatIntel/ThreatIntelProcessEvaluationProvider.vue")
)
const ArtifactsCollect = defineAsyncComponent(() => import("@/components/artifacts/ArtifactsCollect.vue"))
const CodeSource = defineAsyncComponent(() => import("@/components/common/CodeSource.vue"))

const ViewIcon = "iconoir:eye-alt"
const LinkIcon = "carbon:launch"
const { gotoAgent, gotoIndex } = useGoto()
const message = useMessage()
const loading = ref(false)
const showDetails = ref(false)
const assetNameTruncated = computed(() => _truncate(asset.asset_name, { length: 50 }))
const alertContext = ref<AlertContext | null>(null)
const processNameList = computed<string[]>(() => alertContext.value?.context?.process_name || [])
const isInvestigationAvailable = computed(() => processNameList.value.length)

watch(showDetails, val => {
	if (val && !alertContext.value) {
		getAlertContext(asset.alert_context_id)
	}
})

function getAlertContext(alertContextId: number) {
	loading.value = true

	Api.incidentManagement
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
.alert-asset-item {
	&:not(.badge) {
		border-radius: var(--border-radius);
		background-color: var(--bg-color);
		transition: all 0.2s var(--bezier-ease);
		border: var(--border-small-050);
		overflow: hidden;

		&:hover {
			box-shadow: 0px 0px 0px 1px var(--primary-color);
		}

		.main-box {
			.content {
				word-break: break-word;
			}
		}
	}

	&.embedded {
		background-color: var(--bg-secondary-color);
	}

	&.badge {
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
}
</style>
