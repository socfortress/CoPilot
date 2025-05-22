<template>
	<div class="grid-auto-fit-250 grid gap-2">
		<CardKV v-for="item of propsSanitized" :key="item.key">
			<template #key>
				{{ item.key }}
			</template>
			<template #value>
				<template v-if="item.key === 'customer_code' && item.val !== '-'">
					<code class="text-primary cursor-pointer" @click="gotoCustomer({ code: item.val })">
						{{ item.val }}
						<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
					</code>
				</template>
				<template v-else-if="item.key === 'velociraptor_id'">
					<AgentVelociraptorIdForm v-model:velociraptor-id="item.val" :agent @updated="emit('updated')" />
				</template>
				<template v-else>
					{{ item.val ?? "-" }}
				</template>
			</template>
		</CardKV>
	</div>
</template>

<script setup lang="ts">
import type { Agent } from "@/types/agents.d"
import { computed, toRefs } from "vue"
import CardKV from "@/components/common/cards/CardKV.vue"
import Icon from "@/components/common/Icon.vue"
import { useGoto } from "@/composables/useGoto"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import AgentVelociraptorIdForm from "./AgentVelociraptorIdForm.vue"

const props = defineProps<{
	agent: Agent
}>()

const emit = defineEmits<{
	(e: "updated"): void
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
