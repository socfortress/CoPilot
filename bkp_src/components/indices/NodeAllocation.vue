<template>
    <div class="cluster-health">
        <div class="title">
            Nodes Allocation <small class="o-050">({{ indicesAllocation.length }})</small>
        </div>
        <div v-loading="loading">
            <div class="info">
                <template v-if="indicesAllocation.length">
                    <el-scrollbar max-height="500px">
                        <div
                            v-for="node of indicesAllocation"
                            :key="node.id"
                            class="item"
                            :class="[`percent-${getStatusPercent(node.disk_percent)}`, `node-${node.node}`]"
                        >
                            <div class="group">
                                <div class="box">
                                    <div class="value">{{ node.node }}</div>
                                    <div class="label">node</div>
                                </div>
                            </div>
                            <div class="group">
                                <div class="box">
                                    <div class="value">{{ node.disk_total || "-" }}</div>
                                    <div class="label">disk_total</div>
                                </div>
                                <div class="box">
                                    <div class="value">{{ node.disk_used || "-" }}</div>
                                    <div class="label">disk_used</div>
                                </div>
                                <div class="box">
                                    <div class="value">{{ node.disk_available || "-" }}</div>
                                    <div class="label">disk_available</div>
                                </div>
                            </div>
                            <div class="group" v-if="node.disk_percent">
                                <div class="box w-full">
                                    <el-progress
                                        :text-inside="true"
                                        :stroke-width="26"
                                        :percentage="node.disk_percent_value"
                                        :status="getStatusPercent(node.disk_percent_value)"
                                    />
                                </div>
                            </div>
                        </div>
                    </el-scrollbar>
                </template>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { onBeforeMount, ref } from "vue"
import { IndexAllocation } from "@/types/indices.d"
import Api from "@/api"
import { ElMessage } from "element-plus"
import { nanoid } from "nanoid"

const indicesAllocation = ref<IndexAllocation[]>([])
const loading = ref(true)

// TODO: decide with Taylor
function getStatusPercent(percent) {
    if (parseFloat(percent) < 20) return "exception"
    if (parseFloat(percent) < 40) return "warning"
    return "success"
}

function getIndicesAllocation() {
    loading.value = true
    Api.indices
        .getAllocation()
        .then(res => {
            if (res.data.success) {
                indicesAllocation.value = (res.data?.node_allocation || []).map(obj => {
                    obj.id = nanoid()
                    obj.disk_percent_value = parseFloat(obj.disk_percent)
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
                    message: err.response?.data?.message || "Wazuh-Indexer returned Unauthorized. Please check your connector credentials.",
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
            loading.value = false
        })
}

onBeforeMount(() => {
    getIndicesAllocation()
})
</script>

<style lang="scss" scoped>
@import "@/assets/scss/_variables";
@import "@/assets/scss/card-shadow";

.cluster-health {
    padding: var(--size-5) var(--size-6);
    @extend .card-base;
    @extend .card-shadow--small;

    .title {
        font-size: var(--font-size-4);
        font-weight: var(--font-weight-6);
        margin-bottom: var(--size-5);
    }
    .info {
        min-height: 50px;
        margin-left: -5px;
        margin-right: -5px;

        .item {
            padding: var(--size-3) var(--size-4);
            @extend .card-base;
            @extend .card-shadow--small;
            border: 2px solid transparent;
            margin: 5px;

            display: flex;
            flex-direction: column;
            gap: var(--size-6);

            .group {
                display: flex;
                justify-content: space-between;
                gap: var(--size-6);
                flex-grow: 1;
                flex-wrap: wrap;

                .box {
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

                    :deep() {
                        .el-progress-bar__outer {
                            border-radius: 4px;

                            .el-progress-bar__inner {
                                border-radius: 0;
                            }
                        }
                    }

                    &.w-full {
                        width: 100%;
                    }
                }
            }

            &.percent-success {
                border-color: $text-color-success;
            }

            &.percent-warning {
                border-color: $text-color-warning;
            }

            &.percent-exception {
                border-color: $text-color-danger;
            }

            &.node-UNASSIGNED {
                border-color: $text-color-info;
            }

            &:not(:last-child) {
                margin-bottom: var(--size-3);
            }
        }
    }
}
</style>
