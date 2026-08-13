<template>
	<n-spin :show="loading">
		<n-card segmented>
			<template #header>
				<div
					class="max-mobile:flex-col max-mobile:items-start max-mobile:gap-2 flex items-center justify-between gap-4"
				>
					<div>
						<span v-if="currentIndex">Below the details for index</span>
						<span v-else>Select an index to see the details</span>
					</div>
					<div v-if="indices && indices.length" class="max-mobile:w-full">
						<n-select
							v-model:value="selectValue"
							placeholder="Indices list"
							clearable
							:consistent-menu-width="false"
							filterable
							:options="selectOptions"
						></n-select>
					</div>
				</div>
			</template>

			<div v-if="currentIndex">
				<div>
					<IndexCard :index="currentIndex" show-actions @delete="clearCurrentIndex()" />
				</div>
				<n-card class="mt-4 overflow-hidden" content-class="p-0!">
					<n-scrollbar x-scrollable class="w-full">
						<n-table :bordered="false" class="min-w-max">
							<thead>
								<tr>
									<th>Node</th>
									<th>Shard</th>
									<th>Size</th>
									<th>State</th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="shard of filteredShards" :key="shard.id">
									<td>{{ shard.node || "-" }}</td>
									<td>{{ shard.shard || "-" }}</td>
									<td>{{ shard.size || "-" }}</td>
									<td>
										<span class="font-bold" :class="shardStateClass(shard.state)">
											{{ shard.state || "-" }}
										</span>
									</td>
								</tr>
							</tbody>
						</n-table>
					</n-scrollbar>
				</n-card>
			</div>
		</n-card>
	</n-spin>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { IndexShard, IndexStats } from "@/types/indices"
import { NCard, NScrollbar, NSelect, NSpin, NTable, useMessage } from "naive-ui"
import { nanoid } from "nanoid"
import { computed, onBeforeMount, ref, toRefs, watch } from "vue"
import Api from "@/api"
import IndexCard from "@/components/indices/IndexCard.vue"
import { getApiErrorMessage } from "@/utils"

type IndexModel = IndexStats | null | ""

const props = defineProps<{
	indices: IndexStats[] | null
	modelValue: IndexModel
	loading?: boolean
}>()

const emit = defineEmits<{
	(e: "update:modelValue", value: IndexModel): void
}>()

const { indices, modelValue, loading: indicesLoading } = toRefs(props)

const message = useMessage()
const shards = ref<IndexShard[]>([])
const loadingShards = ref(false)
const loading = computed(() => indicesLoading.value || !indices?.value || indices.value === null || loadingShards.value)

const currentIndex = computed<IndexModel>({
	get() {
		return modelValue.value
	},
	set(value) {
		emit("update:modelValue", value)
	}
})

const filteredShards = computed(() =>
	shards.value.filter((shard: IndexShard) => {
		if (!currentIndex.value || typeof currentIndex.value === "string") return false
		return shard.index === currentIndex.value?.index
	})
)

const selectValue = ref<string | undefined>(undefined)
const selectOptions = computed(() => {
	return (indices.value || []).map(o => ({ value: o.index, label: o.index }))
})

watch(modelValue, val => {
	selectValue.value = typeof val !== "string" ? val?.index : undefined
})

watch(selectValue, val => {
	currentIndex.value = (indices.value || []).find(o => o.index === val) || null
})

function clearCurrentIndex() {
	currentIndex.value = null
}

function shardStateClass(state?: string) {
	switch (state) {
		case "STARTED":
			return "text-success"
		case "UNASSIGNED":
			return "text-warning"
		default:
			return ""
	}
}

function getShards() {
	loadingShards.value = true
	Api.wazuh.indices
		.getShards()
		.then(res => {
			if (res.data.success) {
				shards.value = (res.data?.shards || []).map(obj => {
					obj.id = nanoid()
					return obj
				})
			} else {
				message.error(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			if (err.response?.status === 401) {
				message.error(
					getApiErrorMessage(err as ApiError) ||
						"Wazuh-Indexer returned Unauthorized. Please check your connector credentials."
				)
			} else if (err.response?.status === 404) {
				message.error(getApiErrorMessage(err as ApiError) || "No alerts were found.")
			} else {
				message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
			}
		})
		.finally(() => {
			loadingShards.value = false
		})
}

onBeforeMount(() => {
	getShards()
})
</script>
