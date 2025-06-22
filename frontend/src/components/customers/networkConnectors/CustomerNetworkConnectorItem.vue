<template>
	<div>
		<CardEntity hoverable :embedded>
			<template #default>
				{{ serviceName }}
			</template>

			<template v-if="networkConnector.deployed" #footerMain>
				<Badge type="active">
					<template #iconLeft>
						<Icon :name="DeployIcon" :size="13"></Icon>
					</template>
					<template #value>Deployed</template>
				</Badge>
			</template>
			<template #footerExtra>
				<div class="flex flex-wrap gap-3">
					<n-button size="small" @click.stop="showDetails = true">
						<template #icon>
							<Icon :name="InfoIcon"></Icon>
						</template>
						Details
					</n-button>

					<CustomerIntegrationMetaButton
						size="small"
						:customer-code="networkConnector.customer_code"
						:integration-name="serviceName"
					/>

					<CustomerNetworkConnectorActions
						class="flex flex-wrap gap-3"
						:network-connector
						hide-delete-button
						size="small"
						@deployed="emit('deployed')"
						@deleted="emit('deleted')"
						@decommissioned="emit('decommissioned')"
					/>
				</div>
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(400px, 90vh)', overflow: 'hidden' }"
			:title="serviceName"
			:bordered="false"
			segmented
		>
			<div class="grid-auto-fit-200 grid gap-2">
				<CardKV v-for="ak of authKeys" :key="ak.key">
					<template #key>
						{{ ak.key }}
					</template>
					<template #value>
						{{ ak.value || "-" }}
					</template>
				</CardKV>
			</div>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { CustomerNetworkConnector } from "@/types/networkConnectors.d"
import _uniqBy from "lodash/uniqBy"
import { NButton, NModal } from "naive-ui"
import { computed, ref, toRefs } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import Icon from "@/components/common/Icon.vue"
import CustomerIntegrationMetaButton from "../metadata/CustomerIntegrationMetaButton.vue"
import CustomerNetworkConnectorActions from "./CustomerNetworkConnectorActions.vue"

const props = defineProps<{
	networkConnector: CustomerNetworkConnector
	embedded?: boolean
}>()
const emit = defineEmits<{
	(e: "deployed"): void
	(e: "decommissioned"): void
	(e: "deleted"): void
}>()

const { networkConnector, embedded } = toRefs(props)

const DeployIcon = "carbon:deploy"
const InfoIcon = "carbon:information"

const showDetails = ref(false)
const serviceName = computed(() => networkConnector.value.network_connector_service_name)
const authKeys = computed(() => {
	const keys: { key: string; value: string }[] = []

	for (const subscriptions of networkConnector.value.network_connectors_subscriptions) {
		for (const ak of subscriptions.network_connectors_keys) {
			keys.push({
				key: ak.auth_key_name,
				value: ak.auth_value
			})
		}
	}

	return _uniqBy(keys, "key")
})
</script>
