<template>
	<div class="flex items-center gap-2">
		<template v-if="!editing">
			<code class="text-primary cursor-pointer" @click="edit()">
				{{ velociraptorId }}
				<Icon :name="loading ? LoadingIcon : EditIcon" :size="13" class="relative top-0.5" />
			</code>
			<n-tooltip v-if="pinned">
				<template #trigger>
					<n-tag size="small" round :bordered="false" type="info" closable :disabled="loading" @close="unpin()">
						<template #icon>
							<Icon :name="PinIcon" :size="12" />
						</template>
						Pinned
					</n-tag>
				</template>
				Set by hand: the agent sync keeps this ID even when another client has the same hostname. Unpin to let
				the sync match it automatically again.
			</n-tooltip>
		</template>
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
						@click="editing = false"
					/>
				</template>
			</n-input>
			<n-button type="primary" ghost :loading size="small" @click="updateAgent()">
				<span v-if="!loading">Save</span>
			</n-button>
		</n-input-group>
	</div>
</template>

<script setup lang="ts">
import type { Agent } from "@/types/agents"
import type { ApiError } from "@/types/common"
import { NButton, NInput, NInputGroup, NTag, NTooltip, useMessage } from "naive-ui"
import { onBeforeMount, ref, toRefs, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"

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
const PinIcon = "carbon:pin-filled"

const loading = ref(false)
const editing = ref(false)
const message = useMessage()
const velociraptorIdModel = ref<string | null>("")
const pinned = ref(!!agent.value.velociraptor_id_pinned)

watch(
	() => agent.value.velociraptor_id_pinned,
	value => {
		pinned.value = !!value
	}
)

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
					pinned.value = true
					editing.value = false
					emit("updated", velociraptorIdPayload)
				} else {
					message.warning(res.data?.message || "An error occurred. Please try again later.")
				}
			})
			.catch(err => {
				message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
			})
			.finally(() => {
				loading.value = false
			})
	}
}

function unpin() {
	if (agent.value.agent_id) {
		loading.value = true

		Api.agents
			.unpinAgentVelociraptorId(agent.value.agent_id.toString())
			.then(res => {
				if (res.data.success) {
					pinned.value = false
					emit("updated", velociraptorId.value)
				} else {
					message.warning(res.data?.message || "An error occurred. Please try again later.")
				}
			})
			.catch(err => {
				message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
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
