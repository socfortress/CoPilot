<template>
	<div class="page flex flex-col gap-4">
		<div class="flex flex-wrap items-center gap-3">
			<n-button
				quaternary
				class="self-start"
				@click="goBack(routeCustomerHealthcheckAgent(customerCode ?? undefined))"
			>
				<template #icon>
					<Icon :name="BackIcon" />
				</template>
				Back
			</n-button>

			<Badge v-if="headerHealth" type="splitted">
				<template #label>Agent</template>
				<template #value>#{{ headerHealth.agent_id }}</template>
			</Badge>
			<Badge v-if="headerHealth" type="splitted">
				<template #label>Label</template>
				<template #value>{{ headerHealth.label }}</template>
			</Badge>
			<Badge v-if="headerHealth" type="splitted">
				<template #label>IP address</template>
				<template #value>{{ headerHealth.ip_address }}</template>
			</Badge>
		</div>

		<CustomerHealthcheckDetails
			v-if="customerCode && source && agentId"
			:customer-code
			:source
			:agent-id
			:embedded="false"
			@loaded="onLoadedHealth"
		/>
		<n-empty v-else description="Invalid health check agent" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import type { CustomerAgentHealth, CustomerHealthcheckSource } from "@/types/customers"
import { NButton, NEmpty } from "naive-ui"
import { computed, ref } from "vue"
import Badge from "@/components/common/Badge.vue"
import Icon from "@/components/common/Icon.vue"
import CustomerHealthcheckDetails from "@/components/customers/healthcheck/CustomerHealthcheckDetails.vue"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"

const { goBack, routeCustomerHealthcheckAgent } = useNavigation()

const BackIcon = "carbon:arrow-left"

const headerHealth = ref<CustomerAgentHealth | null>(null)

const customerCode = useRouteParam("code")
const agentId = useRouteParam("agentId")
const sourceParam = useRouteParam("source")

const source = computed<CustomerHealthcheckSource | null>(() => {
	const value = sourceParam.value
	return value === "wazuh" || value === "velociraptor" ? value : null
})

function onLoadedHealth(health: CustomerAgentHealth) {
	headerHealth.value = health
}
</script>
