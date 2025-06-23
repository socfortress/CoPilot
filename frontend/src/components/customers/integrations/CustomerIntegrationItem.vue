<template>
	<div>
		<CardEntity hoverable :embedded>
			<template #default>
				{{ serviceName }}
			</template>

			<template v-if="integration.deployed" #footerMain>
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
							<Icon :name="DetailsIcon"></Icon>
						</template>
						Details
					</n-button>

					<CustomerIntegrationMetaButton
						size="small"
						:customer-code="integration.customer_code"
						:integration-name="serviceName"
					/>

					<CustomerIntegrationActions
						class="flex flex-wrap gap-3"
						:integration
						size="small"
						@deployed="emit('deployed')"
						@deleted="emit('deleted')"
					/>
				</div>
			</template>
		</CardEntity>

		<!-- Existing Details Modal -->
		<n-modal
			v-model:show="showDetails"
			preset="card"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(404px, 90vh)', overflow: 'hidden' }"
			:title="serviceName"
			:bordered="false"
			segmented
			display-directive="show"
		>
			<CustomerIntegrationDetails :integration @deleted="emit('deleted')" @updated="integration = $event" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { CustomerIntegration } from "@/types/integrations.d"
import { NButton, NModal } from "naive-ui"
import { computed, defineAsyncComponent, ref } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import CustomerIntegrationMetaButton from "../metadata/CustomerIntegrationMetaButton.vue"
import CustomerIntegrationActions from "./CustomerIntegrationActions.vue"

const { integration: customerIntegration, embedded } = defineProps<{
	integration: CustomerIntegration
	embedded?: boolean
}>()

const emit = defineEmits<{
	(e: "deployed"): void
	(e: "deleted"): void
}>()

const CustomerIntegrationDetails = defineAsyncComponent(() => import("./CustomerIntegrationDetails.vue"))

const DeployIcon = "carbon:deploy"
const DetailsIcon = "carbon:settings-adjust"
const integration = ref(customerIntegration)
const showDetails = ref(false)
const serviceName = computed(() => integration.value.integration_service_name)
</script>
