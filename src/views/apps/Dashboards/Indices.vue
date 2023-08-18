<template>
    <el-scrollbar class="page page-indices">
        <div class="mb-30">
            <IndicesMarquee :indices="indices" @click="setIndex" />
        </div>

        <div class="mb-30">
            <Details :indices="indices" v-model="currentIndex" />
        </div>

        <div class="mb-30">
            <div class="flex">
                <div class="box grow">
                    <ClusterHealth />
                </div>
                <div class="box grow">
                    <UnhealthyIndices :indices="indices" @click="setIndex" />
                </div>
            </div>
        </div>

        <div class="mb-30">
            <div class="flex">
                <div class="box grow">chart 1</div>
                <div class="box grow">chart 2</div>
            </div>
        </div>
    </el-scrollbar>
</template>

<script lang="ts" setup>
import { Index, IndexAllocation, IndexHealth } from "@/types/indices.d"
import Api from "@/api"
import { ElMessage } from "element-plus"
import { computed, onBeforeMount, ref } from "vue"
import IndicesMarquee from "@/components/indices/Marquee.vue"
import ClusterHealth from "@/components/indices/ClusterHealth.vue"
import Details from "@/components/indices/Details.vue"
import UnhealthyIndices from "@/components/indices/UnhealthyIndices.vue"

const indices = ref<Index[]>([])
const indicesAllocation = ref<IndexAllocation[]>([])
const loadingIndex = ref(false)
const loadingAllocation = ref(false)
const loadingDeleteIndex = ref(false)
const currentIndex = ref<Index | null>(null)

const loading = computed(() => loadingIndex.value || loadingAllocation.value)

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

onBeforeMount(() => {
    getIndices()
    getIndicesAllocation()
})
</script>

<style lang="scss" scoped>
@import "@/assets/scss/_variables";
@import "@/assets/scss/card-shadow";

.page-indices {
}
</style>
