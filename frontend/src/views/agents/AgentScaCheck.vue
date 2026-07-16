<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader
			:title="check?.title || `Check #${checkId}`"
			:back-route="routeAgentSca(agentId ?? undefined, policyId ?? undefined)"
		>
			<template #meta>
				<span class="text-secondary font-mono text-sm">{{ policyId }}</span>
			</template>
		</DetailPageHeader>

		<n-spin v-if="agentId && policyId && checkId != null" :show="loading" class="min-h-40">
			<ScaResultItemDetails v-if="check" :data="check" full-width />
			<n-empty v-else-if="!loading" description="SCA check not found" class="h-32 justify-center" />
		</n-spin>
		<n-empty v-else description="Invalid SCA check" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import type { ScaPolicyResult } from "@/types/agents"
import { NEmpty, NSpin } from "naive-ui"
import Api from "@/api"
import ScaResultItemDetails from "@/components/agents/sca/ScaResultItemDetails.vue"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import { useEntityDetails } from "@/composables/useEntityDetails"
import { useNavigation, useRouteIdParam, useRouteParam } from "@/composables/useNavigation"

const { routeAgentSca } = useNavigation()

const agentId = useRouteParam("id")
const policyId = useRouteParam("policyId")
const checkId = useRouteIdParam("checkId")

const { loading, entity: check } = useEntityDetails<ScaPolicyResult, string>({
	entity: () => null,
	id: () =>
		agentId.value && policyId.value && checkId.value != null
			? `${agentId.value}|${policyId.value}|${checkId.value}`
			: null,
	fetch: (_id, signal) =>
		Api.agents
			.getSCAResults(agentId.value as string, policyId.value as string, checkId.value as number, signal)
			.then(res => ({
				entity: res.data.success ? (res.data.sca_policy_results?.[0] ?? null) : null,
				message: res.data.message
			})),
	notFoundMessage: "SCA check not found",
	errorMessage: "An error occurred. Please try again later."
})
</script>
