<template>
    <div class="cluster-health">
        <div class="title">Overall Health</div>
        <div v-loading="loading">
            <div class="info">
                <div class="cluster-card" :class="[`health-${cluster.status}`]" v-if="cluster">
                    <el-scrollbar max-height="500px">
                        <div class="card-wrap">
                            <div class="box" v-for="prop of propsOrder" :key="prop">
                                <template v-if="prop === 'status'">
                                    <div class="value text-uppercase">
                                        <IndexIcon :health="cluster.status" color />
                                        {{ cluster.status }}
                                    </div>
                                </template>
                                <template v-else>
                                    <div class="value">{{ cluster[prop] }}</div>
                                </template>
                                <div class="label">{{ sanitizeLabel(prop) }}</div>
                            </div>
                        </div>
                    </el-scrollbar>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { onBeforeMount, ref } from "vue"
import IndexIcon from "@/components/indices/IndexIcon.vue"
import { ClusterHealth } from "@/types/indices.d"
import Api from "@/api"
import { ElMessage } from "element-plus"

const cluster = ref<ClusterHealth | null>(null)
const loading = ref(true)

const propsOrder = ref([
    "cluster_name",
    "status",
    "active_primary_shards",
    "active_shards",
    "active_shards_percent_as_number",
    "delayed_unassigned_shards",
    "discovered_cluster_manager",
    "discovered_master",
    "initializing_shards",
    "number_of_data_nodes",
    "number_of_in_flight_fetch",
    "number_of_nodes",
    "number_of_pending_tasks",
    "relocating_shards",
    "task_max_waiting_in_queue_millis",
    "timed_out",
    "unassigned_shards"
])

function sanitizeLabel(label: string) {
    return label.replaceAll("_", " ")
}

function getClusterHealth() {
    loading.value = true
    Api.indices
        .getClusterHealth()
        .then(res => {
            cluster.value = res.data.cluster_health
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
            loading.value = false
        })
}

onBeforeMount(() => {
    getClusterHealth()
})
</script>

<style lang="scss" scoped>
@import "@/assets/scss/_variables";
@import "@/assets/scss/card-shadow";

.cluster-health {
    padding: var(--size-5) var(--size-6);
    @extend .card-base;

    .title {
        font-size: var(--font-size-4);
        font-weight: var(--font-weight-6);
        margin-bottom: var(--size-5);
    }
    .info {
        min-height: 50px;

        .cluster-card {
            @extend .card-base;
            @extend .card-shadow--small;
            border: 2px solid transparent;

            .card-wrap {
                padding: var(--size-3) var(--size-4);
                column-width: 12rem;
                column-count: auto;
                column-gap: var(--size-6);
                gap: var(--size-6);

                .box {
                    overflow: hidden;
                    margin-bottom: var(--size-6);
                    .value {
                        font-weight: bold;
                        margin-bottom: 2px;
                        white-space: nowrap;
                    }
                    .label {
                        font-size: var(--font-size-0);
                        font-family: var(--font-mono);
                        opacity: 0.8;
                    }
                }
            }

            &.health-green {
                border-color: $text-color-success;
            }

            &.health-yellow {
                border-color: $text-color-warning;
            }

            &.health-red {
                border-color: $text-color-danger;
            }
        }
    }
}
</style>
