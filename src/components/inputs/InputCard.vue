<template>
    <div class="input-card" :class="[`health-green`]" v-loading="loading">
        <div class="group">
            <div class="box">
                <div class="value">{{ input.title }}</div>
                <div class="label">name</div>
            </div>
            <div class="box">
                <div class="value">{{ input.id }}</div>
                <div class="label">id</div>
            </div>
            <!-- <div class="box">
              <div class="value text-uppercase">
                  <InputIcon :health="input.health" color />
                  {{ input.health }}
              </div>
              <div class="label">health</div>
          </div> -->
        </div>
        <div class="group">
            <div class="box">
                <div class="value">{{ input.port }}</div>
                <div class="label">port</div>
            </div>
            <div class="box">
                <div class="value">{{ input.inputstate }}</div>
                <div class="label">state</div>
            </div>
        </div>
        <div class="group actions" v-if="showActions">
            <div class="box">
                <!--
              <el-tooltip content="Rotate" placement="top" :show-arrow="false">
                  <el-button type="primary" :icon="RefreshIcon" circle />
              </el-tooltip>
            -->
                <el-tooltip content="Start Input" placement="top" :show-arrow="false">
                    <el-button type="primary" :icon="DeleteIcon" circle @click="handleStart" />
                </el-tooltip>
                <el-tooltip content="Stop Input" placement="top" :show-arrow="false">
                    <el-button type="danger" :icon="DeleteIcon" circle @click="handleStop" />
                </el-tooltip>
            </div>
        </div>
    </div>
</template>

<!-- arrow-down-drop-circle
"mdi mdi-arrow-down-drop-circle" -->

<script setup lang="ts">
import { ref, toRefs } from "vue"
import InputIcon from "@/components/inputs/InputIcon.vue"
import { Inputs } from "@/types/graylog.d"
import Api from "@/api"
import { ElMessage, ElMessageBox } from "element-plus"
import { Refresh as RefreshIcon, Delete as DeleteIcon } from "@element-plus/icons-vue"

const emit = defineEmits<{
    (e: "delete"): void
}>()

const props = defineProps<{
    input: Inputs
    showActions?: boolean
}>()
const { input, showActions } = toRefs(props)

const loading = ref(false)

const handleStop = () => {
    ElMessageBox.confirm(`Are you sure you want to stop the Input:<br/><strong>${input.value.title}</strong> ?`, "Warning", {
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
            stopInput()
        })
        .catch(() => {
            ElMessage({
                type: "info",
                message: "Stop canceled"
            })
        })
}

function stopInput() {
    loading.value = true

    Api.graylog
        .stopInput(input.value.id)
        .then(res => {
            if (res.data.success) {
                ElMessage({
                    message: "Input was successfully stopped.",
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
                    message: err.response?.data?.message || "Graylog returned Unauthorized. Please check your connector credentials.",
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

const handleStart = () => {
    ElMessageBox.confirm(`Are you sure you want to start the Input:<br/><strong>${input.value.title}</strong> ?`, "Warning", {
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
            startInput()
        })
        .catch(() => {
            ElMessage({
                type: "info",
                message: "Stop canceled"
            })
        })
}

function startInput() {
    loading.value = true

    Api.graylog
        .startInput(input.value.id)
        .then(res => {
            if (res.data.success) {
                ElMessage({
                    message: "Input was successfully started.",
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
                    message: err.response?.data?.message || "Graylog returned Unauthorized. Please check your connector credentials.",
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

.input-card {
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
