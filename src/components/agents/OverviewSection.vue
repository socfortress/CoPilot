<template>
	<div class="overview-section">
		<div class="property-group">
			<div v-for="item of propsSanitized" :key="item.key" class="property">
				<div class="key">{{ item.key }}</div>
				<div class="value">{{ item.val }}</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, toRefs } from "vue"
import dayjs from "@/utils/dayjs"
import { type Agent } from "@/types/agents.d"
import { useSettingsStore } from "@/stores/settings"

const props = defineProps<{
	agent: Agent
}>()
const { agent } = toRefs(props)

const dFormats = useSettingsStore().dateFormat

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

	return datejs.format(dFormats.datetime)
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

		.property {
			border: var(--border-small-100);
			background-color: var(--bg-secondary-color);
			border-radius: var(--border-radius);
			overflow: hidden;
			flex-basis: 140px;
			flex-grow: 1;

			.key {
				border-bottom: var(--border-small-050);
				padding: 8px 12px;
				font-size: 12px;
			}
			.value {
				font-size: 14px;
				padding: 8px 12px;
				background-color: var(--bg-color);
				font-family: var(--font-family-mono);
				height: 100%;
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
