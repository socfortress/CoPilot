<template>
    <el-scrollbar class="page page-indices">
        <!--

			<div class="section">
				<IndicesMarquee :indices="indices" @click="setIndex" />
			</div>
		-->

        <div class="section">
            <Details :indices="indices" v-model="currentIndex" />
        </div>

        <div class="section">
            <div class="columns">
                <div class="col basis-50">
                    <ClusterHealth />
                </div>
                <div class="col basis-50">
                    <UnhealthyIndices :indices="indices" @click="setIndex" class="stretchy" />
                </div>
            </div>
        </div>

        <div class="section">
            <div class="columns">
                <div class="col basis-20">chart 1</div>
                <div class="col basis-80">
                    <TopIndices :indices="indices" />
                </div>
            </div>
        </div>
    </el-scrollbar>
</template>

<script lang="ts" setup>
import { Index, IndexAllocation } from "@/types/indices.d"
import Api from "@/api"
import { ElMessage } from "element-plus"
import { onBeforeMount, ref } from "vue"
import IndicesMarquee from "@/components/indices/Marquee.vue"
import ClusterHealth from "@/components/indices/ClusterHealth.vue"
import Details from "@/components/indices/Details.vue"
import UnhealthyIndices from "@/components/indices/UnhealthyIndices.vue"
import TopIndices from "@/components/indices/TopIndices.vue"

const indices = ref<Index[]>([])
const indicesAllocation = ref<IndexAllocation[]>([])
const loadingIndex = ref(false)
const loadingAllocation = ref(false)
const currentIndex = ref<Index | null>(null)

function setIndex(index: Index) {
    currentIndex.value = index
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
    .section {
        margin-bottom: var(--size-6);

        .columns {
            display: flex;
            gap: var(--size-6);

            .col {
                flex-grow: 1;
                overflow: hidden;
                &.basis-20 {
                    flex-basis: 20%;
                }
                &.basis-50 {
                    flex-basis: 50%;
                }
                &.basis-80 {
                    flex-basis: 80%;
                }
            }

            .stretchy {
                height: 100%;
                box-sizing: border-box;
            }
        }
    }

    @media (max-width: 1000px) {
        .section {
            .columns {
                flex-direction: column;
            }
        }
    }
}
</style>
