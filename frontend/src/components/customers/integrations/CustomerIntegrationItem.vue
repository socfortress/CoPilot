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

					<!-- Add this new Meta Details button -->
					<n-button size="small" @click.stop="showMetaDetails = true">
						<template #icon>
							<Icon :name="MetaIcon"></Icon>
						</template>
						Meta Details
					</n-button>

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

		<!-- Add this new Meta Details Modal -->
		<n-modal
			v-model:show="showMetaDetails"
			preset="card"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(404px, 90vh)', overflow: 'hidden' }"
			:title="`${serviceName} - Meta Details`"
			:bordered="false"
			segmented
			display-directive="show"
		>
			<CustomerIntegrationMetaDetails
				:customer-code="integration.customer_code"
				:integration-name="serviceName"
			/>
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
const CustomerIntegrationMetaDetails = defineAsyncComponent(() => import("./CustomerIntegrationMetaDetails.vue"))

const DeployIcon = "carbon:deploy"
const DetailsIcon = "carbon:settings-adjust"
const MetaIcon = "carbon:data-base" // Add new icon for Meta Details
const integration = ref(customerIntegration)
const showDetails = ref(false)
const showMetaDetails = ref(false) // Add new ref for Meta Details modal
const serviceName = computed(() => integration.value.integration_service_name)
</script>
