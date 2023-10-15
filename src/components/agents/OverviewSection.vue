<template>
	<div class="overview-section">
		<div class="property-group">
			<n-card v-for="item of propsSanitized" :key="item.key">
				<template #action>{{ item.key }}</template>
				<div class="font-bold">{{ item.val }}</div>
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

const propsSanitized = computed(() => {
	const obj = []
	for (const key in agent.value) {
		if (["wazuh_last_seen", "velociraptor_last_seen"].includes(key)) {
			// @ts-ignore
			obj.push({ key, val: formatDate(agent.value[key]) || "-" })
		} else {
			// @ts-ignore
			obj.push({ key, val: agent.value[key] || "-" })
		}
	}

	return obj
})

const formatDate = (date: string) => {
	const datejs = dayjs(date)
	if (!datejs.isValid()) return date

	return datejs.format("DD/MM/YYYY @ HH:mm")
}
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
