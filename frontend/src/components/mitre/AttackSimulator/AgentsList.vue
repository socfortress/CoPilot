<template>
	<n-spin :show="loading">
		<div class="flex min-h-52 flex-col gap-2 py-0.5">
			<template v-if="list.length">
				<CardEntity
					v-for="item of list"
					:key="item.hostname"
					embedded
					clickable
					hoverable
					:highlighted="item.hostname === selected?.hostname"
					size="small"
					@click="setItem(item)"
				>
					<template #headerMain>
						{{ item.hostname }}
					</template>
					<template #headerExtra>
						<code class="text-primary cursor-pointer" @click.stop="routeAgent(item.agent_id)">
							{{ item.agent_id }}
							<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
						</code>
					</template>
					<template #default>
						{{ item.ip_address }}
						<code>{{ item.label }}</code>
					</template>
					<template #footer>
						<div class="flex flex-wrap items-center gap-2">
							<Icon :name="iconFromOs(item.os)" :size="14" />
							<span>
								{{ item.os }}
							</span>
						</div>
					</template>
				</CardEntity>
			</template>
			<template v-else>
				<n-empty v-if="!loading" description="No items found" class="h-48 justify-center" />
			</template>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { Agent } from "@/types/agents.d"
import { NEmpty, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useNavigation } from "@/composables/useNavigation"
import { iconFromOs } from "@/utils"

const { agentsList, filter } = defineProps<{
	agentsList?: Agent[] | null
	filter?: (agent: Agent) => boolean
}>()

const emit = defineEmits<{
	(e: "loaded", value: Agent[]): void
}>()

const selected = defineModel<Agent | null>("selected", { default: null })

const LinkIcon = "carbon:launch"

const { routeAgent } = useNavigation()
const message = useMessage()
const loading = ref(false)
const list = ref<Agent[]>([])

function getList() {
	loading.value = true

	Api.agents
		.getAgents()
		.then(res => {
			if (res.data.success) {
				const tmpList = res.data?.agents || []
				list.value = filter ? tmpList.filter(filter) : tmpList
				emit("loaded", list.value)
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

function setItem(item: Agent) {
	selected.value = selected.value?.hostname === item.hostname ? null : item
}

onBeforeMount(() => {
	if (agentsList?.length) {
		list.value = agentsList
	} else {
		getList()
	}
})
</script>
