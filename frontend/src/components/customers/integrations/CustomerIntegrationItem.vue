<template>
	<div class="integration-item" :class="{ embedded }">
		<div class="px-4 py-3 flex flex-col gap-3">
			<div class="header-box flex justify-between items-center">
				<div class="id">#{{ integration.id }}</div>
				<div class="actions flex gap-3">
					<Badge v-if="integration.deployed" type="active">
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
				<CustomerIntegrationActions
					class="actions-box"
					:integration="integration"
					hideDeleteButton
					@deployed="emit('deployed')"
					@deleted="emit('deleted')"
				/>
			</div>
			<div class="footer-box flex justify-between items-center gap-4">
				<CustomerIntegrationActions
					class="actions-box"
					:integration="integration"
					hideDeleteButton
					@deployed="emit('deployed')"
					@deleted="emit('deleted')"
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
import type { CustomerIntegration } from "@/types/integrations.d"
import CustomerIntegrationActions from "./CustomerIntegrationActions.vue"
import KVCard from "@/components/common/KVCard.vue"
import _uniqBy from "lodash/uniqBy"

const props = defineProps<{
	integration: CustomerIntegration
	embedded?: boolean
}>()
const { integration, embedded } = toRefs(props)

const emit = defineEmits<{
	(e: "deployed"): void
	(e: "deleted"): void
}>()

const DeployIcon = "carbon:deploy"
const InfoIcon = "carbon:information"

const showDetails = ref(false)
const serviceName = computed(() => integration.value.integration_service_name)
const authKeys = computed(() => {
	const keys: { key: string; value: string }[] = []

	for (const subscriptions of integration.value.integration_subscriptions) {
		for (const ak of subscriptions.integration_auth_keys) {
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
.integration-item {
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
