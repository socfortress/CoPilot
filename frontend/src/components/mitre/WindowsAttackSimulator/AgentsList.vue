<template>
	<n-spin :show="loading">
		<div class="min-h-52">
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
					<template #header>
						{{ item.hostname }}
					</template>
					<template #main>
						{{ item.id }}
					</template>
					<template #footer>
						<pre>{{ item }}</pre>
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

const selected = defineModel<Agent | null>("selected", { default: null })

const message = useMessage()
const loading = ref(false)
const list = ref<Agent[]>([])

function getList() {
	loading.value = true

	Api.agents
		.getAgents()
		.then(res => {
			if (res.data.success) {
				list.value = res.data?.agents || []
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
	getList()
})
</script>
