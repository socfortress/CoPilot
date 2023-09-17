<template>
	<div class="overview-section">
		<div class="property-group">
			<div class="property">
				<div class="label">client_id</div>
				<div class="value">{{ agent.client_id || "-" }}</div>
			</div>
			<div class="property">
				<div class="label">client_last_seen</div>
				<div class="value">{{ formatClientLastSeen || "-" }}</div>
			</div>
			<div class="property">
				<div class="label">ip_address</div>
				<div class="value">{{ agent.ip_address || "-" }}</div>
			</div>
			<div class="property">
				<div class="label">label</div>
				<div class="value">{{ agent.label || "-" }}</div>
			</div>
			<div class="property">
				<div class="label">last_seen</div>
				<div class="value">{{ formatLastSeen || "-" }}</div>
			</div>
			<div class="property">
				<div class="label">os</div>
				<div class="value">{{ agent.os || "-" }}</div>
			</div>
			<div class="property">
				<div class="label">velociraptor_client_version</div>
				<div class="value">{{ agent.velociraptor_client_version || "-" }}</div>
			</div>
			<div class="property">
				<div class="label">wazuh_agent_version</div>
				<div class="value">{{ agent.wazuh_agent_version || "-" }}</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, toRefs } from "vue"
import dayjs from "dayjs"
import { type Agent } from "@/types/agents.d"

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
		grid-gap: var(--size-5);
		grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
		grid-auto-flow: row dense;

		.property {
			background-color: rgb(244, 244, 244);
			padding: var(--size-3);
			position: relative;
			border-radius: 8px;

			.label {
				position: absolute;
				top: -8px;
				@apply text-xs;
				background-color: #8d91a1;
				padding: 1px 6px;
				font-family: var(--font-family-mono);
				border-radius: 5px;
				color: white;
				max-width: calc(100% - var(--size-8));
				overflow: hidden;
				white-space: nowrap;
				text-overflow: ellipsis;
			}

			.value {
				position: relative;
				top: 5px;
			}
		}
	}

	@container (max-width: 500px) {
		.property-group {
			grid-template-columns: repeat(auto-fit, 100%);
		}
	}
}
</style>
