<template>
	<div>
		<CardEntity :embedded :clickable="selectable" :disabled hoverable>
			<template #default>
				<div class="flex items-center gap-3">
					<div v-if="selectable" class="check-box mr-2">
						<n-radio v-model:checked="checked" size="large" />
					</div>
					<div class="flex flex-col gap-1">
						{{ data.name }}
						<p>
							{{ data.description }}
						</p>
					</div>
				</div>
			</template>

			<template #footerMain>
				<div class="flex flex-wrap items-center gap-3">
					<code class="py-1">Auth Keys:</code>
					<Badge v-for="authKey of data.keys" :key="authKey.auth_key_name">
						<template #value>
							{{ authKey.auth_key_name }}
						</template>
					</Badge>
				</div>
			</template>
			<template #footerExtra>
				<EntityDetailsButton size="small" :route="detailRoute" @view="showDetails = true" />
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showDetails"
			display-directive="show"
			preset="card"
			:style="{ maxWidth: 'min(850px, 90vw)', minHeight: 'min(400px, 80vh)', overflow: 'hidden' }"
			:title="data.name"
			:bordered="false"
			content-class="p-0!"
		>
			<NetworkConnectorDetails v-if="type === 'network-connector'" :connector="data" />
			<IntegrationDetails v-else :integration="data" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { ServiceItemData, ServiceItemType } from "./types"
import { NModal, NRadio } from "naive-ui"
import { computed, ref, toRefs } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import EntityDetailsButton from "@/components/common/EntityDetailsButton.vue"
import IntegrationDetails from "@/components/integrations/IntegrationDetails.vue"
import NetworkConnectorDetails from "@/components/networkConnectors/NetworkConnectorDetails.vue"
import { useNavigation } from "@/composables/useNavigation"

const props = defineProps<{
	data: ServiceItemData
	type: ServiceItemType
	embedded?: boolean
	checked?: boolean
	selectable?: boolean
	disabled?: boolean
}>()

const { data, embedded, checked, selectable, disabled } = toRefs(props)

const { routeThirdPartyIntegration, routeNetworkConnector } = useNavigation()

const detailRoute = computed(() =>
	props.type === "integration" ? routeThirdPartyIntegration(data.value.id) : routeNetworkConnector(data.value.id)
)

const showDetails = ref(false)
</script>
