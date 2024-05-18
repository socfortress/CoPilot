<template>
	<div class="flex items-center gap-2">
		<code v-if="!editing" class="cursor-pointer text-primary-color" @click="edit()">
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
						:name="CloseIcon"
						:size="13"
						class="cursor-pointer"
						@click="editing = false"
						v-if="!loading"
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
import { onBeforeMount, ref, toRefs } from "vue"
import Api from "@/api"
import { useMessage, NInput, NButton, NInputGroup } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import type { Agent } from "@/types/agents"

const velociraptorId = defineModel<string>("velociraptorId", { default: "" })

const props = defineProps<{
	agent: Agent
}>()
const { agent } = toRefs(props)

const emit = defineEmits<{
	(e: "updated", value: string): void
}>()

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
