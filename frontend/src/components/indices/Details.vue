<template>
	<n-spin :show="loading">
		<n-card class="index-details-box" segmented>
			<template #header>
				<div class="box-header">
					<div class="title">
						<span v-if="currentIndex">Below the details for index</span>
						<span v-else>Select an index to see the details</span>
					</div>
					<div class="select-box" v-if="indices && indices.length">
						<n-select
							v-model:value="selectValue"
							placeholder="Indices list"
							clearable
							filterable
							:options="selectOptions"
						></n-select>
					</div>
				</div>
			</template>

			<div class="details-box" v-if="currentIndex">
				<div class="info">
					<IndexCard :index="currentIndex" showActions @delete="clearCurrentIndex()" />
				</div>
				<n-card class="shards overflow-hidden" content-style="padding:0">
					<n-scrollbar x-scrollable style="width: 100%">
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
										<span class="shard-state" :class="shard.state">
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
import { computed, onBeforeMount, ref, toRefs, watch } from "vue"
import type { IndexStats, IndexShard } from "@/types/indices.d"
import IndexCard from "@/components/indices/IndexCard.vue"
import Api from "@/api"
import { nanoid } from "nanoid"
import { useMessage, NScrollbar, NSpin, NTable, NSelect, NCard } from "naive-ui"

type IndexModel = IndexStats | null | ""

const emit = defineEmits<{
	(e: "update:modelValue", value: IndexModel): void
}>()

const props = defineProps<{
	indices: IndexStats[] | null
	modelValue: IndexModel
}>()
const { indices, modelValue } = toRefs(props)

const message = useMessage()
const shards = ref<IndexShard[]>([])
const loadingShards = ref(false)
const loading = computed(() => !indices?.value || indices.value === null || loadingShards.value)

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

const currentIndex = computed<IndexModel>({
	get() {
		return modelValue.value
	},
	set(value) {
		emit("update:modelValue", value)
	}
})

function clearCurrentIndex() {
	currentIndex.value = null
}

function getShards() {
	loadingShards.value = true
	Api.indices
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
					err.response?.data?.message ||
						"Wazuh-Indexer returned Unauthorized. Please check your connector credentials."
				)
			} else if (err.response?.status === 404) {
				message.error(err.response?.data?.message || "No alerts were found.")
			} else {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
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

<style lang="scss" scoped>
.index-details-box {
	.box-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		@apply gap-4;
	}

	.details-box {
		.shards {
			@apply mt-4;

			.shard-state {
				font-weight: bold;
				&.STARTED {
					color: var(--success-color);
				}
				&.UNASSIGNED {
					color: var(--warning-color);
				}
			}
		}
	}

	@media (max-width: 700px) {
		.box-header {
			flex-direction: column;
			align-items: flex-start;
			@apply gap-2;

			.select-box {
				width: 100%;
			}
		}
	}
}
</style>
