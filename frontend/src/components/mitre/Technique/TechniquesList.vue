<template>
	<div class="flex flex-col gap-3">
		<div v-for="item of itemsPaginated" :key="item.id">
			<TechniqueCard :id="item.id" :entity="item.entity" @loaded="item.entity = $event" />
		</div>
		<div v-if="list.length" class="flex justify-end">
			<n-pagination
				v-model:page="currentPage"
				v-model:page-size="pageSize"
				:item-count="list.length"
				:page-slot="6"
			/>
		</div>
		<n-empty v-else description="No items found" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import type { MitreTechniqueDetails } from "@/types/mitre.d"
import { NEmpty, NPagination } from "naive-ui"
import { computed, onMounted, ref } from "vue"
import TechniqueCard from "./TechniqueCard.vue"

const { list } = defineProps<{
	list: string[]
}>()

const pageSize = ref(5)
const currentPage = ref(1)
const techniques = ref<{ id: string; entity?: MitreTechniqueDetails }[]>([])

const itemsPaginated = computed(() => {
	const from = (currentPage.value - 1) * pageSize.value
	const to = currentPage.value * pageSize.value

	return techniques.value.slice(from, to)
})

onMounted(() => {
	techniques.value = list.map(o => ({ id: o, entity: undefined }))
})
</script>
