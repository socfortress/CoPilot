<template>
	<SegmentedPage toolbar-height="60px" toolbar-height-mobile="50px" padding="16px" enable-resize>
		<template #sidebar-header>
			<n-button v-if="areAllTacticsSelected" :focusable="false" @click="toggleAllTactics(false)">
				<template #icon>
					<Icon name="carbon:checkbox" :size="16" />
				</template>
				Unselect all
			</n-button>
			<n-button v-else type="primary" :focusable="false" @click="toggleAllTactics(true)">
				<template #icon>
					<Icon name="carbon:checkbox-checked" :size="16" />
				</template>
				Select all
			</n-button>
		</template>
		<template #sidebar-content>
			<n-spin :show="loading">
				<div class="flex flex-col gap-4">
					<div v-for="tactic of tacticsList" :key="tactic.id" class="flex items-center gap-3">
						<n-checkbox
							:checked="isTacticSelected(tactic.id)"
							@update-checked="toggleTacticSelect(tactic.id)"
						>
							<div class="flex items-center gap-2">
								<span>{{ tactic.name }}</span>
								<code class="whitespace-nowrap">{{ tactic.count }}</code>
							</div>
						</n-checkbox>
					</div>
				</div>
				<n-empty v-if="!tacticsList.length" description="No tactics available" class="h-48 justify-center" />
			</n-spin>
		</template>
		<template #main-toolbar>
			<div class="flex items-center gap-4">
				<n-input v-model:value="textFilter" placeholder="Search by technique name" clearable>
					<template #prefix>
						<Icon name="carbon:search" :size="16" />
					</template>
				</n-input>
				<div class="min-w-32 max-w-32">
					<n-checkbox v-model:checked="hideNoAlertsTechniques" class="items-center!" size="large">
						<span class="text-xs/tight">Hide techniques with no alerts</span>
					</n-checkbox>
				</div>
			</div>
		</template>
		<template #main-content>
			<n-spin :show="loading">
				<div class="grid-auto-fill-250 grid gap-2">
					<TechniqueAlertCard
						v-for="technique of filteredTechniques"
						:key="technique.technique_id"
						:entity="technique"
						class="flex"
					/>
				</div>
				<n-empty v-if="!filteredTechniques.length" description="No items found" class="h-48 justify-center" />
			</n-spin>
		</template>
	</SegmentedPage>
</template>

<script setup lang="ts">
import type { MitreTechniquesAlertsQuery, MitreTechniquesAlertsQueryTimeRange } from "@/api/endpoints/mitre"
import type { MitreTechnique } from "@/types/mitre.d"
import { watchDebounced } from "@vueuse/core"
import axios from "axios"
import { NButton, NCheckbox, NEmpty, NInput, NSpin, useMessage } from "naive-ui"
import { computed, ref, toRefs, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import SegmentedPage from "@/components/common/SegmentedPage.vue"
import TechniqueAlertCard from "../TechniqueAlert/TechniqueAlertCard.vue"

const props = defineProps<{
	filters?: { type: string; value: string }[]
}>()

const { filters } = toRefs(props)
const loading = ref(false)
const message = useMessage()
const techniquesList = ref<MitreTechnique[]>([])
const currentPage = ref(1)
const hideNoAlertsTechniques = ref(false)
const textFilter = ref<string | null>(null)
let abortController: AbortController | null = null

const selectedTactics = ref<string[]>([])

const tacticsList = computed(() => {
	const list: { name: string; id: string; count: number }[] = []

	for (const technique of techniquesList.value) {
		for (const tactic of technique.tactics) {
			const savedTactic = list.find(o => o.id === tactic.id)
			if (savedTactic) {
				savedTactic.count += technique.count
			} else {
				list.push({
					name: tactic.name,
					id: tactic.id,
					count: technique.count
				})
			}
		}
	}

	return list
})

const filteredTechniques = computed(() => {
	return techniquesList.value
		.filter(a => {
			for (const tactic of a.tactics) {
				if (selectedTactics.value.includes(tactic.id)) {
					return true
				}
			}

			return false
		})
		.filter(a => !textFilter.value || a.technique_name.toLowerCase().includes(textFilter.value.toLowerCase()))
		.filter(a => !hideNoAlertsTechniques.value || (hideNoAlertsTechniques.value && a.count))
})

const areAllTacticsSelected = computed(() => {
	return selectedTactics.value.length === tacticsList.value.length
})

function isTacticSelected(id: string) {
	return !!selectedTactics.value.find(o => o === id)
}

function toggleTacticSelect(id: string) {
	const index = selectedTactics.value.findIndex(o => o === id)

	if (selectedTactics.value.find(o => o === id)) {
		selectedTactics.value.splice(index, 1)
	} else {
		selectedTactics.value.push(id)
	}
}

function toggleAllTactics(state: boolean) {
	if (state) {
		selectedTactics.value = tacticsList.value.map(o => o.id)
	} else {
		selectedTactics.value = []
	}
}

function resetList() {
	techniquesList.value = []
	currentPage.value = 1
	getList()
}

function nextPage() {
	currentPage.value++
	getList()
}

function getList() {
	abortController?.abort()
	abortController = new AbortController()

	loading.value = true

	const query: MitreTechniquesAlertsQuery = {
		time_range: filters.value?.find(o => o.type === "time_range")?.value as
			| MitreTechniquesAlertsQueryTimeRange
			| undefined,
		size: 300,
		page: currentPage.value,
		rule_level: filters.value?.find(o => o.type === "rule_level")?.value,
		rule_group: filters.value?.find(o => o.type === "rule_group")?.value,
		mitre_field: filters.value?.find(o => o.type === "mitre_field")?.value,
		index_pattern: filters.value?.find(o => o.type === "index_pattern")?.value
	}

	Api.mitre
		.getMitreTechniquesAlerts(query, abortController.signal)
		.then(res => {
			loading.value = false

			if (res.data.success) {
				techniquesList.value = [...techniquesList.value, ...res.data.techniques]
				if (res.data.total_pages > currentPage.value) {
					nextPage()
				}
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			if (!axios.isCancel(err)) {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
				loading.value = false
			}
		})
}

watch(
	tacticsList,
	() => {
		toggleAllTactics(true)
	},
	{ deep: true, immediate: true }
)

watchDebounced(filters, resetList, {
	deep: true,
	debounce: 300,
	immediate: true
})
// MOCK
/*
techniquesList.value = techniques
*/
</script>
