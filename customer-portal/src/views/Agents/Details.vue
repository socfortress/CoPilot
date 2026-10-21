<template>
	<div class="page @container flex flex-col gap-6">
		<AgentDetails
			v-if="agentId"
			:agent-id
			:initial-tab="single(route.query.tab)"
			:initial-search="single(route.query.search)"
			:initial-policy="single(route.query.policy)"
		/>
	</div>
</template>

<script setup lang="ts">
import { useRoute } from "vue-router"
import AgentDetails from "@/components/agents/AgentDetails"

const route = useRoute()
const agentId = route.params.id ? `${route.params.id}` : null

// A link can open a tab filtered to what was clicked (the Exposure page's, #1289).
function single(value: unknown): string | undefined {
	const raw = Array.isArray(value) ? value[0] : value
	return typeof raw === "string" && raw ? raw : undefined
}
</script>
