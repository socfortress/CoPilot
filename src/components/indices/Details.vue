<template>
	<div class="index-details-box" v-loading="loading" :class="{ active: currentIndex }">
		<div class="box-header">
			<div class="title">
				<span v-if="currentIndex">Below the details for index</span>
				<span v-else>Select an index to see the details</span>
			</div>
			<div class="select-box" v-if="indices && indices.length">
				<el-select v-model="currentIndex" placeholder="Indices list" clearable value-key="index" filterable>
					<el-option
						v-for="index in indices"
						:key="index.index"
						:label="index.index"
						:value="index"
					></el-option>
				</el-select>
			</div>
		</div>
		<div class="details-box" v-if="currentIndex">
			<div class="info">
				<IndexCard :index="currentIndex" showActions @delete="clearCurrentIndex()" />
			</div>
			<div class="shards">
				<el-scrollbar>
					<table class="styled">
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
					</table>
				</el-scrollbar>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeMount, ref, toRefs } from "vue"
import { type Index, type IndexShard } from "@/types/indices.d"
import { ElMessage } from "element-plus"
import IndexCard from "@/components/indices/IndexCard.vue"
import Api from "@/api"
import { nanoid } from "nanoid"

type IndexModel = Index | null | ""

const emit = defineEmits<{
	(e: "update:modelValue", value: IndexModel): void
}>()

const props = defineProps<{
	indices: Index[] | null
	modelValue: IndexModel
}>()
const { indices, modelValue } = toRefs(props)

const shards = ref<IndexShard[]>([])
const loadingShards = ref(false)
const loading = computed(() => !indices?.value || indices.value === null || loadingShards.value)

const filteredShards = computed(() =>
	shards.value.filter((shard: IndexShard) => {
		if (!currentIndex.value || typeof currentIndex.value === "string") return false
		return shard.index === currentIndex.value?.index
	})
)

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
				ElMessage({
					message: res.data?.message || "An error occurred. Please try again later.",
					type: "error"
				})
			}
		})
		.catch(err => {
			if (err.response.status === 401) {
				ElMessage({
					message:
						err.response?.data?.message ||
						"Wazuh-Indexer returned Unauthorized. Please check your connector credentials.",
					type: "error"
				})
			} else if (err.response.status === 404) {
				ElMessage({
					message: err.response?.data?.message || "No alerts were found.",
					type: "error"
				})
			} else {
				ElMessage({
					message: err.response?.data?.message || "An error occurred. Please try again later.",
					type: "error"
				})
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
@import "@/assets/scss/_variables";
@import "@/assets/scss/card-shadow";

.index-details-box {
	padding: var(--size-5) var(--size-6);
	border: 2px solid transparent;

	&.active {
		border-color: var(--primary-color);
	}

	.box-header {
		display: flex;
		align-items: center;

		.title {
			margin-right: var(--size-4);
		}

		.select-box {
			.el-select {
				min-width: var(--size-fluid-9);
				max-width: 100%;
			}
		}
	}

	.details-box {
		margin-top: var(--size-6);

		.shards {
			margin-top: var(--size-4);

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

	@media (max-width: 1000px) {
		.box-header {
			flex-direction: column;
			align-items: flex-start;
			gap: var(--size-2);
			.select-box {
				width: 100%;
				.el-select {
					min-width: 100%;
				}
			}
		}
	}
}
</style>
