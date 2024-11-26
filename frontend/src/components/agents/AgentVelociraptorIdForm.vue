<template>
	<div class="flex items-center gap-2">
		<code v-if="!editing" class="text-primary cursor-pointer" @click="edit()">
			{{ velociraptorId }}
			<Icon :name="loading ? LoadingIcon : EditIcon" :size="13" class="relative top-0.5" />
		</code>
		<n-input-group v-else>
			<n-input
				v-model:value="velociraptorIdModel"
				size="small"
				:disabled="loading"
				placeholder="Input velociraptor_id"
			>
				<template #suffix>
					<Icon
						v-if="!loading"
						:name="CloseIcon"
						:size="13"
						class="cursor-pointer"
						@click="(editing = false)"
					/>
				</template>
			</n-input>
			<n-button type="primary" ghost :loading="loading" size="small" @click="updateAgent()">
				<span v-if="!loading">Save</span>
			</n-button>
		</n-input-group>
	</div>
</template>

<script setup lang="ts">
import type { Agent } from "@/types/agents.d"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { NButton, NInput, NInputGroup, useMessage } from "naive-ui"
import { onBeforeMount, ref, toRefs } from "vue"

const props = defineProps<{
	agent: Agent
}>()

const emit = defineEmits<{
	(e: "updated", value: string): void
}>()

const velociraptorId = defineModel<string>("velociraptorId", { default: "" })

const { agent } = toRefs(props)

const LoadingIcon = "eos-icons:loading"
const EditIcon = "uil:edit-alt"
const CloseIcon = "carbon:close-filled"

const loading = ref(false)
const editing = ref(false)
const message = useMessage()
const velociraptorIdModel = ref<string | null>("")

function edit() {
	editing.value = true
	velociraptorIdModel.value = velociraptorId.value
}

function updateAgent() {
	if (agent.value.agent_id) {
		loading.value = true

		const velociraptorIdPayload = velociraptorIdModel.value || ""

		Api.agents
			.updateAgent(agent.value.agent_id.toString(), { velociraptor_id: velociraptorIdPayload })
			.then(res => {
				if (res.data.success) {
					velociraptorId.value = velociraptorIdPayload
					editing.value = false
					emit("updated", velociraptorIdPayload)
				} else {
					message.warning(res.data?.message || "An error occurred. Please try again later.")
				}
			})
			.catch(err => {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			})
			.finally(() => {
				loading.value = false
			})
	}
}

onBeforeMount(() => {
	velociraptorIdModel.value = velociraptorId.value || ""
})
</script>
