<template>
    <div class="page-agent scrollable only-y">
        <div class="agent-toolbar">
            <div class="back-btn">
                <i class="mdi mdi-arrow-left" @click="gotoAgents()"></i>
                <span> Agents list </span>
            </div>
            <div class="delete-btn" @click.stop="handleDelete">Delete Agent</div>
        </div>
        <div class="page-header card-base card-shadow--small flex" :class="{ critical: agent?.critical_asset, online: isOnline }">
            <div class="box grow">
                <div class="title">
                    <div class="critical" :class="{ active: agent?.critical_asset }">
                        <el-tooltip content="Toggle Critical Assets" placement="top" :show-arrow="false">
                            <el-button
                                text
                                :icon="StarIcon"
                                :type="agent?.critical_asset ? 'warning' : ''"
                                circle
                                @click.stop="toggleCritical(agent?.agent_id, agent?.critical_asset)"
                            />
                        </el-tooltip>
                    </div>
                    <h1 v-if="agent?.hostname">
                        {{ agent?.hostname }}
                    </h1>
                    <span class="online-badge" v-if="isOnline"> ONLINE </span>
                </div>
                <el-breadcrumb separator="/">
                    <el-breadcrumb-item :to="{ path: '/' }"><i class="mdi mdi-home-outline"></i></el-breadcrumb-item>
                    <el-breadcrumb-item>Agent</el-breadcrumb-item>
                    <el-breadcrumb-item v-if="agent?.agent_id">#{{ agent?.agent_id }}</el-breadcrumb-item>
                </el-breadcrumb>
            </div>
            <div class="menu-btn align-vertical" @click="sidebarOpen = !sidebarOpen">
                <i class="mdi mdi-menu align-vertical-middle"></i>
            </div>
        </div>
        <div class="flex">
            <div class="sidebar scrollable" :class="{ open: sidebarOpen }">
                <el-button size="small" class="close-btn" @click="sidebarOpen = false">close</el-button>
                <ul>
                    <li v-for="i in 20" :key="i">Sidebar Item {{ i }}</li>
                </ul>
            </div>
            <div class="main-content box grow card-base card-shadow--small p-24">
                <div class="property-group" v-if="agent">
                    <div class="property">
                        <div class="label">client_id</div>
                        <div class="value">{{ agent.client_id || "-" }}</div>
                    </div>
                    <div class="property">
                        <div class="label">client_last_seen</div>
                        <div class="value">{{ formatClientLastSeen || "-" }}</div>
                    </div>
                    <div class="property">
                        <div class="label">ip_address</div>
                        <div class="value">{{ agent.ip_address || "-" }}</div>
                    </div>
                    <div class="property">
                        <div class="label">label</div>
                        <div class="value">{{ agent.label || "-" }}</div>
                    </div>
                    <div class="property">
                        <div class="label">last_seen</div>
                        <div class="value">{{ formatLastSeen || "-" }}</div>
                    </div>
                    <div class="property">
                        <div class="label">os</div>
                        <div class="value">{{ agent.os || "-" }}</div>
                    </div>
                    <div class="property">
                        <div class="label">velociraptor_client_version</div>
                        <div class="value">{{ agent.velociraptor_client_version || "-" }}</div>
                    </div>
                    <div class="property">
                        <div class="label">wazuh_agent_version</div>
                        <div class="value">{{ agent.wazuh_agent_version || "-" }}</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, computed } from "vue"
import { useRoute } from "vue-router"
import dayjs from "dayjs"
import { ElMessage } from "element-plus"
import Api from "@/api"
import { Agent, AgentVulnerabilities } from "@/types/agents"
import { handleDeleteAgent, isAgentOnline, toggleAgentCritical } from "@/components/agents/utils"
import { Star as StarIcon } from "@element-plus/icons-vue"
import { useRouter } from "vue-router"

const router = useRouter()
const sidebarOpen = ref(false)
const route = useRoute()
const loadingAgent = ref(false)
const loadingVulnerabilities = ref(false)
const agent = ref<Agent | null>(null)
const vulnerabilities = ref<AgentVulnerabilities[]>([])

const isOnline = computed(() => {
    return isAgentOnline(agent.value?.last_seen)
})

const formatLastSeen = computed(() => {
    const lastSeenDate = dayjs(agent.value.last_seen)
    if (!lastSeenDate.isValid()) return agent.value.last_seen

    return lastSeenDate.format("DD/MM/YYYY @ HH:mm")
})

const formatClientLastSeen = computed(() => {
    const lastSeenDate = dayjs(agent.value.client_last_seen)
    if (!lastSeenDate.isValid()) return agent.value.last_seen

    return lastSeenDate.format("DD/MM/YYYY @ HH:mm")
})

function getAgent(id: string) {
    console.log("agent", id)

    loadingAgent.value = true

    Api.agents
        .getAgents(id)
        .then(res => {
            if (res.data.success) {
                agent.value = res.data.agent || null
            } else {
                ElMessage({
                    message: res.data?.message || "An error occurred. Please try again later.",
                    type: "error"
                })
                router.push(`/agents`).catch(err => {})
            }
        })
        .catch(err => {
            ElMessage({
                message: err.response?.data?.message || "An error occurred. Please try again later.",
                type: "error"
            })
            router.push(`/agents`).catch(err => {})
        })
        .finally(() => {
            loadingAgent.value = false
        })
}

function getVulnerabilities(id: string) {
    console.log("Vulnerabilities", id)

    loadingVulnerabilities.value = true

    Api.agents
        .agentVulnerabilities(id)
        .then(res => {
            if (res.data.success) {
                vulnerabilities.value = res.data.vulnerabilities || []
            } else {
                ElMessage({
                    message: res.data?.message || "An error occurred. Please try again later.",
                    type: "warning"
                })
            }
        })
        .catch(err => {
            ElMessage({
                message: err.response?.data?.message || "An error occurred. Please try again later.",
                type: "error"
            })
        })
        .finally(() => {
            console.log(vulnerabilities.value)
            loadingVulnerabilities.value = false
        })
}

function toggleCritical(agentId: string, criticalStatus: boolean) {
    toggleAgentCritical({
        agentId,
        criticalStatus,
        cbBefore: () => {
            loadingAgent.value = true
        },
        cbSuccess: () => {
            if (agent.value?.critical_asset !== undefined) {
                agent.value.critical_asset = !criticalStatus
            }
        },
        cbAfter: () => {
            loadingAgent.value = false
        }
    })
}

function handleDelete() {
    handleDeleteAgent({
        agent: agent.value,
        cbBefore: () => {
            loadingAgent.value = true
        },
        cbSuccess: () => {
            gotoAgents()
        },
        cbAfter: () => {
            loadingAgent.value = false
        }
    })
}

function gotoAgents() {
    router.push(`/agents`).catch(err => {})
}

onBeforeMount(() => {
    if (route.params.id) {
        getAgent(route.params.id.toString())
        getVulnerabilities(route.params.id.toString())
    } else {
        router.replace(`/agents`).catch(err => {})
    }
})
</script>

<style lang="scss" scoped>
@import "@/assets/scss/_variables";

.page-agent {
    padding-left: 20px;
    padding-right: 15px;
    padding-bottom: 20px;

    .agent-toolbar {
        margin-top: 16px;
        display: flex;
        justify-content: space-between;
        align-items: center;

        .back-btn {
            cursor: pointer;
            opacity: 0.8;
            font-size: 14px;

            i {
                font-size: 20px;
            }

            span {
                position: relative;
                top: -3px;
                margin-left: 4px;
            }
        }

        .delete-btn {
            opacity: 0.8;
            cursor: pointer;
            font-size: 14px;
        }
    }

    .page-header {
        margin-top: 12px;
        margin-bottom: 20px;
        min-height: 60px;
        border: 2px solid transparent;

        .title {
            display: flex;
            align-items: center;
            line-height: 1;

            h1 {
                margin: 0;
                font-size: var(--font-size-4);
            }

            .critical {
                margin-right: 6px;
                margin-left: -8px;

                &:deep() {
                    .el-button {
                        width: 36px;
                        height: 36px;
                    }
                    .el-icon {
                        width: var(--font-size-3);
                        height: var(--font-size-3);

                        svg {
                            height: var(--font-size-3);
                            width: var(--font-size-3);
                        }
                    }
                }
            }

            .online-badge {
                border: 2px solid $text-color-success;
                color: $text-color-success;
                font-weight: bold;
                margin-left: 10px;
                border-radius: 6px;
                font-size: var(--font-size-0);
                padding: var(--size-1) var(--size-2);
            }
        }

        .menu-btn {
            color: $text-color-primary;
            font-size: 20px;
            display: none;
            cursor: pointer;
        }

        &.critical {
            border-color: $text-color-warning;
        }
    }

    .sidebar {
        box-sizing: border-box;
        padding: 24px;
        min-width: 250px;
        margin-left: -24px;

        .close-btn {
            display: none;
            width: 100%;
            margin-bottom: 10px;
        }

        ul {
            width: 100%;
            list-style: none;
            padding: 0;
            margin: 0;
        }
        li {
            box-sizing: border-box;
            width: 100%;
            list-style: none;
            padding: 15px 20px;
            border-bottom: 1px solid transparentize($text-color-primary, 0.9);
            cursor: pointer;
            position: relative;

            &::after {
                content: "";
                display: block;
                width: 0%;
                height: 100%;
                background: $text-color-primary;
                position: absolute;
                top: 0;
                left: 0;
                opacity: 0;
                transition: all 0.5s;
            }

            &:hover {
                &::after {
                    width: 100%;
                    opacity: 0.3;
                }
            }
        }
    }

    .main-content {
        container-type: inline-size;
        padding: var(--size-5);

        .property-group {
            width: 100%;
            display: grid;
            grid-gap: var(--size-5);
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            grid-auto-flow: row dense;

            .property {
                background-color: rgb(244, 244, 244);
                padding: var(--size-3);
                position: relative;
                border-radius: 8px;

                .label {
                    position: absolute;
                    top: -8px;
                    font-size: var(--font-size-0);
                    background-color: #8d91a1;
                    padding: 1px 6px;
                    font-family: var(--font-mono);
                    border-radius: 5px;
                    color: white;
                    max-width: calc(100% - var(--size-8));
                    overflow: hidden;
                    white-space: nowrap;
                    text-overflow: ellipsis;
                }

                .value {
                    position: relative;
                    top: 5px;
                }
            }
        }

        @container (max-width: 500px) {
            .property-group {
                grid-template-columns: repeat(auto-fit, 100%);
            }
        }
    }
}

@media (max-width: 768px) {
    .page-agent {
        padding-left: 5px;
        padding-right: 5px;

        .page-header {
            .menu-btn {
                display: block;
            }
        }
        .sidebar {
            .close-btn {
                display: block;
            }

            margin: 0;
            text-align: center;
            position: absolute;
            background: white;
            color: #000;
            top: 5px;
            left: -100%;
            opacity: 0;
            bottom: 5px;
            box-shadow: 40px 0px 160px 80px rgba(0, 0, 0, 0.3);
            border-top-right-radius: 4px;
            border-bottom-right-radius: 4px;
            transition: all 0.5s;

            li {
                border-bottom: 1px solid #eee;
            }

            &.open {
                opacity: 1;
                left: 0;
                z-index: 999;
            }
        }
    }
}
</style>
