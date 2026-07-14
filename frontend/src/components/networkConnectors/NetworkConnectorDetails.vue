<template>
	<n-spin :show="loading">
		<CardEntity v-if="resolvedConnector" :embedded>
			<template #headerMain>
				<span class="text-default text-lg font-bold">
					{{ resolvedConnector.name }}
				</span>
			</template>

			<template #default>
				<p v-if="resolvedConnector.description" class="text-secondary mb-4">
					{{ resolvedConnector.description }}
				</p>
				<Markdown v-if="resolvedConnector.details" :source="resolvedConnector.details" />
				<n-empty v-else description="No connector details" class="h-32 justify-center" />
			</template>

			<template #footerMain>
				<div class="flex flex-wrap items-center gap-3">
					<code class="py-1">Auth Keys:</code>
					<Badge v-for="authKey of resolvedConnector.keys" :key="authKey.auth_key_name">
						<template #value>{{ authKey.auth_key_name }}</template>
					</Badge>
				</div>
			</template>

			<template v-if="$slots.footerExtra" #footerExtra>
				<slot name="footerExtra" />
			</template>
		</CardEntity>
	</n-spin>
</template>

<script setup lang="ts">
import type { ServiceItemData } from "@/components/services/types"
import type { NetworkConnector } from "@/types/network-connectors"
import { NEmpty, NSpin } from "naive-ui"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Markdown from "@/components/common/Markdown.vue"
import { useEntityDetails } from "@/composables/useEntityDetails"

const props = withDefaults(
	defineProps<{
		connector?: ServiceItemData | NetworkConnector | null
		connectorId?: number | null
		embedded?: boolean
	}>(),
	{ embedded: true }
)

const emit = defineEmits<{
	(e: "loaded", value: ServiceItemData): void
}>()

function toServiceItemData(connector: NetworkConnector): ServiceItemData {
	return {
		id: connector.id,
		name: connector.network_connector_name,
		description: connector.description,
		details: connector.network_connector_details,
		keys: connector.network_connector_keys
	}
}

function normalizeConnector(connector: ServiceItemData | NetworkConnector): ServiceItemData {
	if ("network_connector_name" in connector) {
		return toServiceItemData(connector)
	}

	return connector
}

const { loading, entity: resolvedConnector } = useEntityDetails<ServiceItemData, number>({
	entity: () => (props.connector ? normalizeConnector(props.connector) : null),
	id: () => props.connectorId,
	fetch: (id, signal) =>
		Api.networkConnectors.getAvailableNetworkConnector(id, signal).then(res => ({
			entity:
				res.data.success && res.data.network_connector
					? toServiceItemData(res.data.network_connector)
					: null,
			message: res.data.message
		})),
	notFoundMessage: "Network connector not found.",
	errorMessage: "Failed to load network connector.",
	onLoaded: value => emit("loaded", value)
})

defineExpose({ loading, resolvedConnector })
</script>
