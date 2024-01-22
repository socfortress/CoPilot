<template>
	<div class="integration-item" :class="{ embedded }">
		<div class="px-4 py-3 flex flex-col gap-3">
			<div class="header-box flex justify-between items-center">
				<div class="id">#{{ integration.id }}</div>
				<div class="actions">
					<Badge type="cursor" @click.stop="showDetails = true">
						<template #iconLeft>
							<Icon :name="DetailsIcon" :size="14"></Icon>
						</template>
						<template #value>Details</template>
					</Badge>
				</div>
			</div>
			<div class="main-box flex items-center gap-3">
				<div class="content flex flex-col gap-1 grow">
					<div class="title">{{ serviceName }}</div>
				</div>
				<div class="actions-box">
					<n-button
						v-if="isOffice365"
						:loading="loadingOffice365Provision"
						@click="office365Provision()"
						type="success"
						secondary
					>
						<template #icon><Icon :name="DeployIcon"></Icon></template>
						Deploy Integration
					</n-button>
				</div>
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
import { NModal, NButton, useMessage } from "naive-ui"
import type { CustomerIntegration } from "@/types/integrations"
import KVCard from "@/components/common/KVCard.vue"
import _uniqBy from "lodash/uniqBy"
import Api from "@/api"

const props = defineProps<{
	integration: CustomerIntegration
	embedded?: boolean
}>()
const { integration, embedded } = toRefs(props)

const emit = defineEmits<{
	(e: "deployed"): void
}>()

const DetailsIcon = "carbon:settings-adjust"
const DeployIcon = "carbon:deploy"

const loadingOffice365Provision = ref(false)
const message = useMessage()
const showDetails = ref(false)
const serviceName = computed(() => integration.value.integration_service_name)
const customerCode = computed(() => integration.value.customer_code)

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

const isOffice365 = computed(() => serviceName.value === "Office365")

function office365Provision() {
	loadingOffice365Provision.value = true

	Api.integrations
		.office365Provision(customerCode.value, serviceName.value)
		.then(res => {
			if (res.data.success) {
				emit("deployed")
				message.success(res.data?.message || "Customer integration successfully deployed.")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingOffice365Provision.value = false
		})
}
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

	&.embedded {
		background-color: var(--bg-secondary-color);
	}

	&:hover {
		box-shadow: 0px 0px 0px 1px inset var(--primary-color);
	}
}
</style>
