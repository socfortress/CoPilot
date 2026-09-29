<template>
	<div class="page @container flex flex-col gap-6">
		<AgentsOverviewStatsCards :stats :loading />
		<AgentsList @stats="stats = $event" @loading="loading = $event" />
	</div>
</template>

<script setup lang="ts">
import type { AgentsStats } from "@/types/agents"
import { ref } from "vue"
import AgentsOverviewStatsCards from "@/components/agents/AgentsOverviewStatsCards.vue"
import AgentsList from "@/components/agents/List.vue"

// Counted server-side over every agent in scope, whatever page or filter the list shows.
const stats = ref<AgentsStats>({ total: 0, active: 0, critical: 0, offline: 0 })
const loading = ref(false)
</script>
