<template>
	<div class="page flex flex-col gap-4">
		<n-button quaternary class="self-start" @click="goBack">
			<template #icon>
				<Icon :name="BackIcon" />
			</template>
			Back
		</n-button>

		<CustomerHealthcheckDetails
			v-if="customerCode && source && agentId"
			:customer-code
			:source
			:agent-id
			:embedded="false"
		/>
		<n-empty v-else description="Invalid health check agent" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import type { CustomerHealthcheckSource } from "@/types/customers"
import { NButton, NEmpty } from "naive-ui"
import { computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import CustomerHealthcheckDetails from "@/components/customers/healthcheck/CustomerHealthcheckDetails.vue"
import Icon from "@/components/common/Icon.vue"

const route = useRoute()
const router = useRouter()

const BackIcon = "carbon:arrow-left"

const customerCode = computed(() => {
	const raw = route.params.code
	if (!raw) return null
	return Array.isArray(raw) ? raw[0] : String(raw)
})

const source = computed<CustomerHealthcheckSource | null>(() => {
	const raw = route.params.source
	if (!raw) return null
	const value = Array.isArray(raw) ? raw[0] : String(raw)
	return value === "wazuh" || value === "velociraptor" ? value : null
})

const agentId = computed(() => {
	const raw = route.params.agentId
	if (!raw) return null
	return Array.isArray(raw) ? raw[0] : String(raw)
})

function goBack() {
	if (window.history.length > 1) {
		router.back()
		return
	}

	if (customerCode.value) {
		router.push({ name: "Customer", params: { code: customerCode.value } })
		return
	}

	router.push({ name: "Customers" })
}
</script>
