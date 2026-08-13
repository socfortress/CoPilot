<template>
	<div>
		<div v-if="badge" class="flex items-center gap-1">
			<code class="text-primary leading-none">{{ asset.asset_name }}</code>
			<EntityDetailsButton
				size="tiny"
				:route="routeIncidentManagementAlertAsset(asset.alert_linked, asset.id)"
				@view="openDetails()"
			/>
		</div>
		<CardEntity v-else :embedded hoverable>
			<template #default>{{ asset.asset_name }}</template>
			<template #mainExtra>
				<div class="flex justify-between gap-2">
					<div class="flex flex-wrap items-center gap-3">
						<Badge type="splitted">
							<template #label>Index</template>
							<template #value>
								<div class="flex h-full items-center">
									<code
										class="text-primary cursor-pointer leading-none"
										@click.stop="routeIndex(asset.index_name).navigate()"
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
										@click.stop="routeAgent(asset.agent_id).navigate()"
									>
										{{ asset.agent_id }}
										<Icon :name="LinkIcon" :size="14" class="relative top-0.5" />
									</code>
								</div>
							</template>
						</Badge>
					</div>

					<EntityDetailsButton
						size="small"
						:route="routeIncidentManagementAlertAsset(asset.alert_linked, asset.id)"
						@view="openDetails()"
					/>
				</div>
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			content-class="p-0!"
			:style="{ maxWidth: 'min(825px, 90vw)', minHeight: 'min(550px, 90vh)', overflow: 'hidden' }"
			:bordered="false"
			:title="assetNameTruncated"
			segmented
		>
			<AlertAssetOverview :asset />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { AlertAsset } from "@/types/incidentManagement/alerts"
import _truncate from "lodash/truncate"
import { NModal } from "naive-ui"
import { computed, ref } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import EntityDetailsButton from "@/components/common/EntityDetailsButton.vue"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/useNavigation"
import AlertAssetOverview from "./AlertAssetOverview.vue"

const { asset, embedded, badge } = defineProps<{ asset: AlertAsset; embedded?: boolean; badge?: boolean }>()

const LinkIcon = "carbon:launch"
const { routeAgent, routeIndex, routeIncidentManagementAlertAsset } = useNavigation()
const showDetails = ref(false)
const assetNameTruncated = computed(() => _truncate(asset.asset_name, { length: 50 }))

function openDetails() {
	showDetails.value = true
}
</script>
