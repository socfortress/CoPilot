<template>
	<div class="overview-section">
		<div class="property-group">
			<KVCard v-for="item of propsSanitized" :key="item.key">
				<template #key>{{ item.key }}</template>
				<template #value>
					<template v-if="item.key === 'customer_code' && item.val !== '-'">
						<code class="cursor-pointer text-primary-color" @click="gotoCustomer({ code: item.val })">
							{{ item.val }}
							<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
						</code>
					</template>
					<template v-else-if="item.key === 'velociraptor_id'">
						<AgentVelociraptorIdForm v-model:velociraptorId="item.val" :agent @updated="emit('updated')" />
					</template>
					<template v-else>
						{{ item.val ?? "-" }}
					</template>
				</template>
			</KVCard>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, toRefs } from "vue"
import { formatDate } from "@/utils"
import { type Agent } from "@/types/agents.d"
import { useSettingsStore } from "@/stores/settings"
import KVCard from "@/components/common/KVCard.vue"
import Icon from "@/components/common/Icon.vue"
import { useGoto } from "@/composables/useGoto"
import AgentVelociraptorIdForm from "./AgentVelociraptorIdForm.vue"

const emit = defineEmits<{
	(e: "updated"): void
}>()

const props = defineProps<{
	agent: Agent
}>()
const { agent } = toRefs(props)

const LinkIcon = "carbon:launch"
const dFormats = useSettingsStore().dateFormat
const { gotoCustomer } = useGoto()

const propsSanitized = computed(() => {
	const obj = []
	for (const key in agent.value) {
		if (["wazuh_last_seen", "velociraptor_last_seen"].includes(key)) {
			obj.push({ key, val: formatDate(Reflect.get(agent.value, key), dFormats.datetime) || "-" })
		} else {
			obj.push({ key, val: Reflect.get(agent.value, key) || "-" })
		}
	}

	return obj
})
</script>

<style lang="scss" scoped>
.overview-section {
	container-type: inline-size;

	.property-group {
		width: 100%;
		display: grid;
		@apply gap-2;
		grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
		grid-auto-flow: row dense;
	}

	@container (max-width: 500px) {
		.property-group {
			grid-template-columns: repeat(auto-fit, 100%);
		}
	}
}
</style>
