<template>
	<n-spin :show="loading">
		<CardEntity v-if="resolvedIntegration" :embedded>
			<template #headerMain>
				<span class="text-default text-lg font-bold">
					{{ resolvedIntegration.name }}
				</span>
			</template>

			<template #default>
				<p v-if="resolvedIntegration.description" class="text-secondary mb-4">
					{{ resolvedIntegration.description }}
				</p>
				<Markdown v-if="resolvedIntegration.details" :source="resolvedIntegration.details" />
				<n-empty v-else description="No integration details" class="h-32 justify-center" />
			</template>

			<template #footerMain>
				<div class="flex flex-wrap items-center gap-3">
					<code class="py-1">Auth Keys:</code>
					<Badge v-for="authKey of resolvedIntegration.keys" :key="authKey.auth_key_name">
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
import type { AvailableIntegration } from "@/types/integrations"
import { NEmpty, NSpin } from "naive-ui"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Markdown from "@/components/common/Markdown.vue"
import { useEntityDetails } from "@/composables/useEntityDetails"

const props = withDefaults(
	defineProps<{
		integration?: ServiceItemData | AvailableIntegration | null
		integrationId?: number | null
		embedded?: boolean
	}>(),
	{ embedded: true }
)

const emit = defineEmits<{
	(e: "loaded", value: ServiceItemData): void
}>()

function toServiceItemData(integration: AvailableIntegration): ServiceItemData {
	return {
		id: integration.id,
		name: integration.integration_name,
		description: integration.description,
		details: integration.integration_details,
		keys: integration.auth_keys
	}
}

function normalizeIntegration(integration: ServiceItemData | AvailableIntegration): ServiceItemData {
	if ("integration_name" in integration) {
		return toServiceItemData(integration)
	}

	return integration
}

const { loading, entity: resolvedIntegration } = useEntityDetails<ServiceItemData, number>({
	entity: () => (props.integration ? normalizeIntegration(props.integration) : null),
	id: () => props.integrationId,
	fetch: (id, signal) =>
		Api.integrations.getAvailableIntegration(id, signal).then(res => ({
			entity:
				res.data.success && res.data.available_integration
					? toServiceItemData(res.data.available_integration)
					: null,
			message: res.data.message
		})),
	notFoundMessage: "Integration not found.",
	errorMessage: "Failed to load integration.",
	onLoaded: value => emit("loaded", value)
})

defineExpose({ loading, resolvedIntegration })
</script>
