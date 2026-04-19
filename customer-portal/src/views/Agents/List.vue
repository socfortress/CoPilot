<template>
	<div class="page @container flex flex-col gap-6">
		<AgentsOverviewStatsCards :stats :loading />
		<AgentsList @loaded="agents = $event" @loading="loading = $event" />
	</div>
</template>

<script setup lang="ts">
import type { AgentsStats } from "@/components/agents/AgentsOverviewStatsCards.vue"
import type { Agent } from "@/types/agents"
import { computed, ref } from "vue"
import AgentsOverviewStatsCards from "@/components/agents/AgentsOverviewStatsCards.vue"
import AgentsList from "@/components/agents/List.vue"

const agents = ref<Agent[]>([])
const stats = computed<AgentsStats>(() => ({
	total: agents.value.length,
	active: agents.value.filter(agent => agent.wazuh_agent_status === "active").length,
	critical: agents.value.filter(agent => agent.critical_asset).length,
	offline: agents.value.filter(
		agent => agent.wazuh_agent_status === "disconnected" || agent.wazuh_agent_status === "never_connected"
	).length
}))
const loading = ref(false)
</script>
