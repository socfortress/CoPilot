<template>
	<n-spin :show="loading">
		<div class="flex min-h-52 flex-col gap-2 py-0.5">
			<template v-if="list.length">
				<CardEntity
					v-for="item of list"
					:key="item.name"
					embedded
					clickable
					hoverable
					:highlighted="item.name === selected?.name"
					size="small"
					@click="setItem(item)"
				>
					<template #header>
						{{ item.name }}
					</template>
					<template #default>
						{{ item.description }}
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
import type { MatchingParameter } from "@/types/artifacts"
import { NEmpty, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"

const { techniqueId, parametersList } = defineProps<{
	techniqueId: string
	parametersList?: MatchingParameter[] | null
}>()

const emit = defineEmits<{
	(e: "loaded", value: MatchingParameter[]): void
}>()

const selected = defineModel<MatchingParameter | null>("selected", { default: null })

const message = useMessage()
const loading = ref(false)
const list = ref<MatchingParameter[]>([])

function getList() {
	loading.value = true

	Api.artifacts
		.getParameters("Windows.AttackSimulation.AtomicRedTeam", techniqueId)
		.then(res => {
			if (res.data.success) {
				list.value = res.data?.matching_parameters || []
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

function setItem(item: MatchingParameter) {
	selected.value = selected.value?.name === item.name ? null : item
}

onBeforeMount(() => {
	if (parametersList?.length) {
		list.value = parametersList
	} else {
		getList()
	}
})
</script>
