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
import _uniq from "lodash/uniqBy"
import { NEmpty, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import { getOS } from "@/utils"

const { techniqueId, parametersList, osList } = defineProps<{
	techniqueId: string
	parametersList?: MatchingParameter[] | null
	osList: string[]
}>()

const emit = defineEmits<{
	(e: "loaded", value: MatchingParameter[]): void
}>()

const selected = defineModel<MatchingParameter | null>("selected", { default: null })

const message = useMessage()
const loading = ref(false)
const list = ref<MatchingParameter[]>([])

async function getList() {
	loading.value = true

	try {
		const proms = []
		for (const os of osList) {
			if (getOS(os) === "Linux") {
				proms.push(Api.artifacts.getParameters("Linux.AttackSimulation.AtomicRedTeam", techniqueId))
			} else if (getOS(os) === "Windows") {
				proms.push(Api.artifacts.getParameters("Windows.AttackSimulation.AtomicRedTeam", techniqueId))
			}
		}

		const parametersListResponse = await Promise.all(proms)

		let fullList: MatchingParameter[] = []

		for (const res of parametersListResponse) {
			fullList = [...fullList, ...res.data.matching_parameters]
		}

		list.value = _uniq(fullList, "name")
		emit("loaded", list.value)
	} catch (err: any) {
		// TODO: remove any
		message.error(err.response?.data?.message || "An error occurred. Please try again later.")
	} finally {
		loading.value = false
	}
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
