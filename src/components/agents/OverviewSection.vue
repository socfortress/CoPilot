<template>
	<div class="overview-section">
		<div class="property-group">
			<n-card>
				<template #action>client_id</template>
				<div class="font-bold">{{ agent.client_id || "-" }}</div>
			</n-card>
			<n-card>
				<template #action>client_last_seen</template>
				<div class="font-bold">{{ formatClientLastSeen || "-" }}</div>
			</n-card>
			<n-card>
				<template #action>ip_address</template>
				<div class="font-bold">{{ agent.ip_address || "-" }}</div>
			</n-card>
			<n-card>
				<template #action>label</template>
				<div class="font-bold">{{ agent.label || "-" }}</div>
			</n-card>
			<n-card>
				<template #action>last_seen</template>
				<div class="font-bold">{{ formatLastSeen || "-" }}</div>
			</n-card>
			<n-card>
				<template #action>os</template>
				<div class="font-bold">{{ agent.os || "-" }}</div>
			</n-card>
			<n-card>
				<template #action>velociraptor_client_version</template>
				<div class="font-bold">{{ agent.velociraptor_client_version || "-" }}</div>
			</n-card>
			<n-card>
				<template #action>wazuh_agent_version</template>
				<div class="font-bold">{{ agent.wazuh_agent_version || "-" }}</div>
			</n-card>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, toRefs } from "vue"
import dayjs from "dayjs"
import { type Agent } from "@/types/agents.d"
import { NCard } from "naive-ui"

const props = defineProps<{
	agent: Agent
}>()
const { agent } = toRefs(props)

const formatLastSeen = computed(() => {
	const lastSeenDate = dayjs(agent.value.last_seen)
	if (!lastSeenDate.isValid()) return agent.value.last_seen

	return lastSeenDate.format("DD/MM/YYYY @ HH:mm")
})

const formatClientLastSeen = computed(() => {
	const lastSeenDate = dayjs(agent.value.client_last_seen)
	if (!lastSeenDate.isValid()) return agent.value.last_seen

	return lastSeenDate.format("DD/MM/YYYY @ HH:mm")
})
</script>

<style lang="scss" scoped>
.overview-section {
	container-type: inline-size;

	.property-group {
		width: 100%;
		display: grid;
		@apply gap-2;
		grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
		grid-auto-flow: row dense;
	}

	@container (max-width: 500px) {
		.property-group {
			grid-template-columns: repeat(auto-fit, 100%);
		}
	}
}
</style>
