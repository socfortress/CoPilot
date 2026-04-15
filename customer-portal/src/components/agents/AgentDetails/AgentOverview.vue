<template>
	<EntityDetailsCard :fields>
		<template #suffix>
			<n-button type="primary" @click="handleCriticalAssetUpdateSuccess(true)">Update Critical Asset</n-button>
		</template>
	</EntityDetailsCard>
</template>

<script setup lang="ts">
import type { Field } from "@/components/common/entity/EntityDetailsCard.vue"
import type { Agent } from "@/types/agents"
import _omit from "lodash/omit"
import { NButton } from "naive-ui"
import { computed } from "vue"
import EntityDetailsCard from "@/components/common/entity/EntityDetailsCard.vue"

const props = defineProps<{
	agent: Agent
}>()

const emit = defineEmits<{
	(e: "criticalAssetUpdated", value: boolean): void
}>()

const fields = computed<Field[]>(() =>
	Object.entries(_omit(props.agent, ["critical_asset"])).map(([key, value]) => ({
		label: key,
		value
	}))
)

function handleCriticalAssetUpdateSuccess(payload: boolean) {
	emit("criticalAssetUpdated", payload)
}
</script>
