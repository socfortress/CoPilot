<template>
    <el-scrollbar class="page page-indices">
        <div class="mb-30">
            <IndicesMarquee :indices="indices" @click="setIndex" />
        </div>

        <div class="index-details-box" :class="{ active: currentIndex }">
            <div class="title">Select an index to see the details</div>
            <div class="select-box">
                <el-select v-model="currentIndex" placeholder="Index list" clearable value-key="index" filterable>
                    <el-option v-for="index in indices" :key="index.index" :label="index.index" :value="index"></el-option>
                </el-select>
            </div>
        </div>

        <div>
            <ClusterHealth />
        </div>
    </el-scrollbar>
</template>

<script lang="ts" setup>
import { Index, IndexAllocation, IndexHealth, IndexShard } from "@/types/indices.d"
import Api from "@/api"
import { ElMessage } from "element-plus"
import { computed, onBeforeMount, ref } from "vue"
import IndicesMarquee from "@/components/indices/Marquee.vue"
import ClusterHealth from "@/components/indices/ClusterHealth.vue"

const indices = ref<Index[]>([])
const shards = ref<IndexShard[]>([])
const indicesAllocation = ref<IndexAllocation[]>([])
const loadingIndex = ref(false)
const loadingShards = ref(false)
const loadingAllocation = ref(false)
const loadingDeleteIndex = ref(false)
const currentIndex = ref<Index | null>(null)
/*
const filteredIndices = computed(() => indices.value.filter((index: Index) => index.index === currentIndex.value?.index))
const filteredShards = computed(() => shards.value.filter((shard: IndexShard) => shard.index === currentIndex.value?.index))
const unhealthyIndices = computed(() =>
    indices.value.filter((index: Index) => index.health === IndexHealth.YELLOW || index.health === IndexHealth.RED)
)
const loading = computed(() => loadingIndex.value || loadingShards.value || loadingAllocation.value)
*/
function setIndex(index: Index) {
    currentIndex.value = index
}

function deleteIndex(index: Index) {
    loadingDeleteIndex.value = true

    Api.indices
        .deleteIndex(index.index)
        .then(() => {
            ElMessage({
                message: "Index was successfully deleted.",
                type: "success"
            })

            getIndices()
        })
        .catch(err => {
            if (err.response.status === 401) {
                ElMessage({
                    message: "Wazuh-Indexer returned Unauthorized. Please check your connector credentials.",
                    type: "error"
                })
            } else if (err.response.status === 404) {
                ElMessage({
                    message: err.response?.data?.message || "An error occurred. Please try again later.",
                    type: "error"
                })
            } else {
                ElMessage({
                    message: "An error occurred. Please try again later.",
                    type: "error"
                })
            }
        })
        .finally(() => {
            loadingDeleteIndex.value = false
        })
}

function getIndicesAllocation() {
    loadingAllocation.value = true
    Api.indices
        .getAllocation()
        .then(res => {
            indicesAllocation.value = res.data.node_allocation
        })
        .catch(err => {
            if (err.response.status === 401) {
                ElMessage({
                    message: "Wazuh-Indexer returned Unauthorized. Please check your connector credentials.",
                    type: "error"
                })
            } else if (err.response.status === 404) {
                ElMessage({
                    message: "No alerts were found.",
                    type: "error"
                })
            } else {
                ElMessage({
                    message: "An error occurred. Please try again later.",
                    type: "error"
                })
            }
        })
        .finally(() => {
            loadingAllocation.value = false
        })
}

function getIndices() {
    loadingIndex.value = true

    Api.indices
        .getIndices()
        .then(res => {
            indices.value = res.data.indices
        })
        .catch(err => {
            if (err.response.status === 401) {
                ElMessage({
                    message: "Wazuh-Indexer returned Unauthorized. Please check your connector credentials.",
                    type: "error"
                })
            } else if (err.response.status === 404) {
                ElMessage({
                    message: "No alerts were found.",
                    type: "error"
                })
            } else {
                ElMessage({
                    message: "An error occurred. Please try again later.",
                    type: "error"
                })
            }
        })
        .finally(() => {
            loadingIndex.value = false
        })
}

function getShards() {
    loadingShards.value = true
    Api.indices
        .getShards()
        .then(res => {
            shards.value = res.data.shards
        })
        .catch(err => {
            if (err.response.status === 401) {
                ElMessage({
                    message: "Wazuh-Indexer returned Unauthorized. Please check your connector credentials.",
                    type: "error"
                })
            } else if (err.response.status === 404) {
                ElMessage({
                    message: "No alerts were found.",
                    type: "error"
                })
            } else {
                ElMessage({
                    message: "An error occurred. Please try again later.",
                    type: "error"
                })
            }
        })
        .finally(() => {
            loadingShards.value = false
        })
}

onBeforeMount(() => {
    getIndices()
    getShards()
    getIndicesAllocation()
})
</script>

<style lang="scss" scoped>
@import "@/assets/scss/_variables";
@import "@/assets/scss/card-shadow";

.page-indices {
    .index-details-box {
        padding: var(--size-6);
        @extend .card-base;
        &.active {
            border: 2px solid $text-color-accent;
            @extend .card-shadow--small;
        }
    }
}
</style>
