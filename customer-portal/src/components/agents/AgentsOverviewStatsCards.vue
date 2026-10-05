<template>
	<n-spin :show="loading">
		<StatusStrip
			:total="stats.total"
			entity="Agents"
			:icon="ICONS.agents"
			:cells="agentStatusCells(stats)"
			:split="agentStatusSplit(stats)"
		/>
	</n-spin>
</template>

<script setup lang="ts">
import type { AgentsStats } from "@/types/agents"
import { NSpin } from "naive-ui"
import StatusStrip from "@/components/common/StatusStrip.vue"
import { ICONS } from "@/const"
import { agentStatusCells, agentStatusSplit } from "./agentStats"

const { stats } = defineProps<{
	stats: AgentsStats
	loading: boolean
}>()
</script>
