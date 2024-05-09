<template>
	<div class="network-connector-item" :class="{ embedded }">
		<div class="px-4 py-3 flex flex-col gap-3">
			<div class="header-box flex justify-between items-center">
				<div class="id">#{{ networkConnector.id }}</div>
				<div class="actions flex gap-3">
					<Badge v-if="networkConnector.deployed" type="active">
						<template #iconLeft>
							<Icon :name="DeployIcon" :size="13"></Icon>
						</template>
						<template #value>Deployed</template>
					</Badge>
					<n-button size="small" @click.stop="showDetails = true">
						<template #icon>
							<Icon :name="InfoIcon"></Icon>
						</template>
					</n-button>
				</div>
			</div>
			<div class="main-box flex items-center gap-3">
				<div class="content flex flex-col gap-1 grow">
					<div class="title">{{ serviceName }}</div>
				</div>
				<CustomerNetworkConnectorActions
					class="actions-box"
					:networkConnector="networkConnector"
					hideDeleteButton
					@deployed="emit('deployed')"
					@deleted="emit('deleted')"
					@decommissioned="emit('decommissioned')"
				/>
			</div>
			<div class="footer-box flex justify-between items-center gap-4">
				<CustomerNetworkConnectorActions
					class="actions-box"
					:networkConnector="networkConnector"
					hideDeleteButton
					@deployed="emit('deployed')"
					@deleted="emit('deleted')"
					@decommissioned="emit('decommissioned')"
					:size="'small'"
				/>
			</div>
		</div>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(400px, 90vh)', overflow: 'hidden' }"
			:title="serviceName"
			:bordered="false"
			segmented
		>
			<div class="grid gap-2 grid-auto-flow-200">
				<KVCard v-for="ak of authKeys" :key="ak.key">
					<template #key>{{ ak.key }}</template>
					<template #value>{{ ak.value || "-" }}</template>
				</KVCard>
			</div>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import Badge from "@/components/common/Badge.vue"
import { computed, ref, toRefs } from "vue"
import { NModal, NButton } from "naive-ui"
import CustomerNetworkConnectorActions from "./CustomerNetworkConnectorActions.vue"
import KVCard from "@/components/common/KVCard.vue"
import _uniqBy from "lodash/uniqBy"
import type { CustomerNetworkConnector } from "@/types/networkConnectors"

const props = defineProps<{
	networkConnector: CustomerNetworkConnector
	embedded?: boolean
}>()
const { networkConnector, embedded } = toRefs(props)

const emit = defineEmits<{
	(e: "deployed"): void
	(e: "decommissioned"): void
	(e: "deleted"): void
}>()

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

<style lang="scss" scoped>
.network-connector-item {
	border-radius: var(--border-radius);
	background-color: var(--bg-color);
	border: var(--border-small-050);
	transition: all 0.2s var(--bezier-ease);

	.header-box {
		font-size: 13px;
		.id {
			font-family: var(--font-family-mono);
			word-break: break-word;
			color: var(--fg-secondary-color);
			line-height: 1.2;
		}
	}

	.main-box {
		.content {
			word-break: break-word;
		}
	}

	.footer-box {
		display: none;
		font-size: 13px;
		margin-top: 10px;
	}

	&.embedded {
		background-color: var(--bg-secondary-color);
	}

	&:hover {
		box-shadow: 0px 0px 0px 1px inset var(--primary-color);
	}

	@container (max-width: 450px) {
		.main-box {
			.actions-box {
				display: none;
			}
		}
		.footer-box {
			display: flex;
		}
	}
}
</style>
