<template>
    <div class="index-card" :class="[`health-${index.health}`]" v-loading="loading">
        <div class="group">
            <div class="box">
                <div class="value">{{ index.index }}</div>
                <div class="label">name</div>
            </div>
            <div class="box">
                <div class="value text-uppercase">
                    <IndexIcon :health="index.health" color />
                    {{ index.health }}
                </div>
                <div class="label">health</div>
            </div>
        </div>
        <div class="group">
            <div class="box">
                <div class="value">{{ index.store_size }}</div>
                <div class="label">store_size</div>
            </div>
            <div class="box">
                <div class="value">{{ index.docs_count }}</div>
                <div class="label">docs_count</div>
            </div>
            <div class="box">
                <div class="value">{{ index.replica_count }}</div>
                <div class="label">replica_count</div>
            </div>
        </div>
        <div class="group actions" v-if="showActions">
            <div class="box">
                <!--
                <el-tooltip content="Rotate" placement="top" :show-arrow="false">
                    <el-button type="primary" :icon="RefreshIcon" circle />
                </el-tooltip>
              -->
                <el-tooltip content="Delete" placement="top" :show-arrow="false">
                    <el-button type="danger" :icon="DeleteIcon" circle @click="handleDelete" />
                </el-tooltip>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, toRefs } from "vue"
import IndexIcon from "@/components/indices/IndexIcon.vue"
import { Index } from "@/types/indices.d"
import Api from "@/api"
import { ElMessage, ElMessageBox } from "element-plus"
import { Refresh as RefreshIcon, Delete as DeleteIcon } from "@element-plus/icons-vue"

const emit = defineEmits<{
    (e: "delete"): void
}>()

const props = defineProps<{
    index: Index
    showActions?: boolean
}>()
const { index, showActions } = toRefs(props)

const loading = ref(false)

const handleDelete = () => {
    ElMessageBox.confirm(`Are you sure you want to delete the index:<br/><strong>${index.value.index}</strong> ?`, "Warning", {
        confirmButtonText: "Yes I'm sure",
        confirmButtonClass: "el-button--warning",
        cancelButtonText: "Cancel",
        type: "warning",
        dangerouslyUseHTMLString: true,
        customStyle: {
            width: "90%",
            maxWidth: "400px"
        }
    })
        .then(() => {
            deleteIndex()
        })
        .catch(() => {
            ElMessage({
                type: "info",
                message: "Delete canceled"
            })
        })
}

function deleteIndex() {
    loading.value = true

    Api.indices
        .deleteIndex(index.value.index)
        .then(res => {
            if (res.data.success) {
                ElMessage({
                    message: "Index was successfully deleted.",
                    type: "success"
                })

                emit("delete")
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
                    message: err.response?.data?.message || "An error occurred. Please try again later.",
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
</script>

<style lang="scss" scoped>
@import "@/assets/scss/_variables";
@import "@/assets/scss/card-shadow";

.index-card {
    padding: var(--size-3) var(--size-4);
    @extend .card-base;
    @extend .card-shadow--small;
    border: 2px solid transparent;

    display: flex;
    justify-content: space-between;
    gap: var(--size-6);
    flex-wrap: wrap;

    .group {
        display: flex;
        justify-content: space-between;
        gap: var(--size-6);
        flex-grow: 1;
        flex-wrap: wrap;

        .box {
            flex-grow: 1;

            .value {
                font-weight: bold;
                margin-bottom: 2px;
                white-space: nowrap;
            }
            .label {
                white-space: nowrap;
                font-size: var(--font-size-0);
                font-family: var(--font-mono);
                opacity: 0.8;
            }
        }
        &.actions {
            flex-grow: 0;
            .box {
                padding: var(--size-2) var(--size-2);
                background-color: rgba(0, 0, 0, 0.07);
                display: flex;
                align-items: center;
                border-radius: var(--radius-6);
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
</style>
