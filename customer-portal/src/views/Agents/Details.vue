<template>
	<div class="page @container flex flex-col gap-6">
		<AgentDetails v-if="agentId" :agent-id />
	</div>
</template>

<script setup lang="ts">
import { useRoute } from "vue-router"
import AgentDetails from "@/components/agents/AgentDetails"

const route = useRoute()
const agentId = route.params.id ? `${route.params.id}` : null
</script>
