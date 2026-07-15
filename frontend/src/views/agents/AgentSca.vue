<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader :title="sca?.name || policyId || undefined" :back-route="routeAgent(agentId ?? undefined)">
			<template #meta>
				<span class="text-secondary font-mono text-sm">{{ policyId }}</span>
				<span v-if="agent" class="text-secondary text-sm">{{ agent.hostname }}</span>
			</template>
		</DetailPageHeader>

		<n-spin v-if="agentId && policyId" :show="loading" class="min-h-40">
			<ScaItem v-if="sca && agent" :sca :agent full-width />
			<n-empty v-else-if="!loading" description="SCA policy not found" class="h-32 justify-center" />
		</n-spin>
		<n-empty v-else description="Invalid SCA policy" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import type { Agent, AgentSca } from "@/types/agents"
import type { ApiError } from "@/types/common"
import { NEmpty, NSpin, useMessage } from "naive-ui"
import { ref, watch } from "vue"
import Api from "@/api"
import ScaItem from "@/components/agents/sca/ScaItem.vue"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"
import { getApiErrorMessage } from "@/utils"

const { routeAgent } = useNavigation()

const message = useMessage()
const loading = ref(false)
const agent = ref<Agent | null>(null)
const sca = ref<AgentSca | null>(null)

const agentId = useRouteParam("id")
const policyId = useRouteParam("policyId")

// ScaItem needs the whole agent too — its results tab queries by agent
function load(id: string, policy: string) {
	loading.value = true

	Promise.all([Api.agents.getAgents(id), Api.agents.getSCA(id, policy)])
		.then(([agentRes, scaRes]) => {
			if (agentRes.data.success) {
				agent.value = agentRes.data.agents?.[0] || null
			} else {
				message.warning(agentRes.data?.message || "An error occurred. Please try again later.")
			}

			if (scaRes.data.success) {
				sca.value = scaRes.data.sca?.[0] || null

				if (!sca.value) {
					message.warning("SCA policy not found")
				}
			} else {
				message.warning(scaRes.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

watch(
	[agentId, policyId],
	([id, policy]) => {
		agent.value = null
		sca.value = null

		if (id && policy) {
			load(id, policy)
		}
	},
	{ immediate: true }
)
</script>
