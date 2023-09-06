<template>
    <div class="agent-card" :class="{ critical: agent.critical_asset }" v-loading="loading">
        <div class="wrapper">
            <div class="agent-header">
                <div class="title">
                    <el-tooltip :content="`${isOnline ? 'online' : 'last seen'} - ${formatLastSeen}`" placement="top" :show-arrow="false">
                        <div class="hostname" :class="{ online: isOnline }">{{ agent.hostname }}</div>
                    </el-tooltip>
                    <div class="critical" :class="{ active: agent.critical_asset }">
                        <el-tooltip content="Toggle Critical Assets" placement="top" :show-arrow="false">
                            <el-button
                                text
                                :icon="StarIcon"
                                :type="agent.critical_asset ? 'warning' : ''"
                                circle
                                @click="toggleAgentCritical(agent.agent_id, agent.critical_asset)"
                            />
                        </el-tooltip>
                    </div>
                </div>
                <div class="info">#{{ agent.agent_id }} / {{ agent.label }}</div>
            </div>
            <div class="agent-info">
                <div class="os" :title="agent.os">
                    {{ agent.os }}
                </div>
                <div class="ip-address" :title="agent.ip_address">{{ agent.ip_address }}</div>
            </div>

            <div class="agent-actions" v-if="showActions">
                <div class="box">
                    <el-tooltip content="Delete" placement="top" :show-arrow="false">
                        <el-button type="danger" :icon="DeleteIcon" circle @click="handleDelete" />
                    </el-tooltip>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed, ref, toRefs } from "vue"
import { Agent } from "@/types/agents.d"
import dayjs from "dayjs"
import Api from "@/api"
import { isAgentOnline } from "./utils"
import { ElMessage, ElMessageBox } from "element-plus"
import { Star as StarIcon, Delete as DeleteIcon } from "@element-plus/icons-vue"

const emit = defineEmits<{
    (e: "delete"): void
}>()

const props = defineProps<{
    agent: Agent
    showActions?: boolean
}>()
const { agent, showActions } = toRefs(props)

const loading = ref(false)

const isOnline = computed(() => {
    return isAgentOnline(agent.value.last_seen)
})
const formatLastSeen = computed(() => {
    const lastSeenDate = dayjs(agent.value.last_seen)
    if (!lastSeenDate.isValid()) return agent.value.last_seen

    return lastSeenDate.format("DD/MM/YYYY @ HH:mm")
})

const handleDelete = () => {
    ElMessageBox.confirm(`Are you sure you want to delete the agent:<br/><strong>${agent.value.label}</strong> ?`, "Warning", {
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
            deleteAgent()
        })
        .catch(() => {
            ElMessage({
                type: "info",
                message: "Delete canceled"
            })
        })
}

function deleteAgent() {
    loading.value = true

    Api.agents
        .deleteAgent(agent.value.agent_id)
        .then(res => {
            if (res.data.success) {
                ElMessage({
                    message: "Agent was successfully deleted.",
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
                    message: err.response?.data?.message || "Agent Delete returned Unauthorized.",
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

function toggleAgentCritical(agentId, criticalStatus) {
    loading.value = agentId
    const method = criticalStatus ? "markNonCritical" : "markCritical"

    Api.agents[method](agentId)
        .then(res => {
            if (res.data.success) {
                ElMessage({
                    message: "Agent Criticality Updated Successfully",
                    type: "success"
                })

                agent.value.critical_asset = !criticalStatus
            } else {
                ElMessage({
                    message: res.data?.message || "Failed to Update Agent Criticality.",
                    type: "error"
                })
            }
        })
        .catch(err => {
            if (err.response.status === 401) {
                ElMessage({
                    message: err.response?.data?.message || "Agent Criticality Update returned Unauthorized.",
                    type: "error"
                })
            } else {
                ElMessage({
                    message: err.response?.data?.message || "Failed to Update Agent Criticality",
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

.agent-card {
    container-type: inline-size;
    @extend .card-base;
    @extend .card-shadow--small;
    overflow: hidden;
    border: 2px solid transparent;
    max-width: 100%;
    padding: var(--size-3) var(--size-4);
    box-sizing: border-box;
    transition: all 0.3s;

    .wrapper {
        display: flex;
        gap: var(--size-6);
        flex-direction: row;
        align-items: center;

        .agent-header {
            display: flex;
            flex-direction: column;
            min-width: 300px;

            .title {
                display: flex;
                align-items: center;
                gap: var(--size-2);
                margin-bottom: 4px;

                .hostname {
                    font-weight: bold;
                    white-space: nowrap;
                    line-height: 32px;
                    height: 32px;
                    background-color: transparent;
                    border-radius: 4px;
                    border: 1px solid $text-color-info;
                    border-color: transparent;
                    box-sizing: border-box;
                    overflow: hidden;
                    text-overflow: ellipsis;

                    &.online {
                        padding: 0px 15px;
                        background-color: rgba(19, 206, 102, 0.1);
                        color: $text-color-success;
                        border-color: $text-color-success;
                    }
                }
            }
            .info {
                font-family: var(--font-mono);
                font-size: var(--font-size-0);
                opacity: 0.7;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                margin-left: 2px;
            }
        }

        .agent-info {
            display: flex;
            flex-direction: column;
            flex-grow: 1;
            overflow: hidden;

            .os {
                line-height: 32px;
                height: 32px;
                margin-bottom: 4px;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            .ip-address {
                white-space: nowrap;
                font-size: var(--font-size-0);
                font-family: var(--font-mono);
                opacity: 0.7;
                overflow: hidden;
                text-overflow: ellipsis;
            }
        }

        .agent-actions {
            display: flex;

            .box {
                padding: var(--size-2) var(--size-2);
                background-color: rgba(0, 0, 0, 0.07);
                display: flex;
                align-items: center;
                border-radius: var(--radius-6);
            }
        }
    }

    &.critical {
        border-color: $text-color-warning;
    }

    &:hover {
        cursor: pointer;
        @extend .card-shadow--medium;
        border-color: #e3e8ec;
    }

    @container (max-width: 550px) {
        .wrapper {
            gap: var(--size-5);

            .agent-header {
                min-width: initial;
            }
        }
    }
    @container (max-width: 480px) {
        .wrapper {
            flex-wrap: wrap;
            gap: var(--size-4);

            .agent-header {
                order: 0;
                flex-grow: 1;
            }
            .agent-info {
                order: 2;
                width: 100%;
            }
            .agent-actions {
                order: 1;
            }
        }
    }
    @container (max-width: 380px) {
        .wrapper {
            flex-wrap: wrap;
            gap: var(--size-3);

            .agent-header {
                order: 0;
                width: 100%;
            }
            .agent-info {
                order: 1;
                width: 100%;
            }
            .agent-actions {
                order: 2;
                width: 100%;
                justify-content: flex-end;
            }
        }
    }
}
</style>
