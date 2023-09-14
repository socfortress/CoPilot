<template>
    <div class="page-agent">
        <div class="agent-toolbar">
            <div class="back-btn" @click="gotoAgents()">
                <i class="mdi mdi-arrow-left"></i>
                <span> Agents list </span>
            </div>
            <div class="delete-btn" @click.stop="handleDelete" v-if="agent">Delete Agent</div>
        </div>
        <div
            class="page-header card-base card-shadow--small flex"
            :class="{ critical: agent?.critical_asset, online: isOnline }"
            v-loading="loadingAgent"
        >
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
        <div class="wrapper">
            <div class="sidebar scrollable" :class="{ open: sidebarOpen }">
                <el-button size="small" class="close-btn" @click="sidebarOpen = false">close</el-button>
                <ul>
                    <li :class="{ active: activePage === 'overview' }" @click="activePage = 'overview'">Overview</li>
                    <li :class="{ active: activePage === 'vulnerabilities' }" @click="activePage = 'vulnerabilities'">Vulnerabilities</li>
                    <li :class="{ active: activePage === 'alerts' }" @click="activePage = 'alerts'">Alerts</li>
                </ul>
            </div>
            <div class="main-content box grow card-base card-shadow--small scrollable only-y">
                <div v-if="agent" v-loading="loadingAgent">
                    <OverviewSection :agent="agent" v-if="activePage === 'overview'" />

                    <VulnerabilitiesSection :agent="agent" v-show="activePage === 'vulnerabilities'" />

                    <template v-if="activePage === 'alerts'">...yet to be implemented...</template>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, computed } from "vue"
import { useRoute } from "vue-router"
import { ElMessage } from "element-plus"
import Api from "@/api"
import { Agent } from "@/types/agents"
import { handleDeleteAgent, isAgentOnline, toggleAgentCritical } from "@/components/agents/utils"
import { Star as StarIcon } from "@element-plus/icons-vue"
import { useRouter } from "vue-router"
import VulnerabilitiesSection from "@/components/agents/VulnerabilitiesSection.vue"
import OverviewSection from "@/components/agents/OverviewSection.vue"

type AgentPages = "overview" | "vulnerabilities" | "alerts"

const router = useRouter()
const sidebarOpen = ref(false)
const route = useRoute()
const loadingAgent = ref(false)
const activePage = ref<AgentPages>("overview")
const agent = ref<Agent | null>(null)

const isOnline = computed(() => {
    return isAgentOnline(agent.value?.last_seen)
})

function getAgent(id: string) {
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
    router.push(`/agents`).catch(() => {})
}

onBeforeMount(() => {
    if (route.params.id) {
        getAgent(route.params.id.toString())
    } else {
        router.replace(`/agents`).catch(() => {})
    }
})
</script>

<style lang="scss" scoped>
@import "@/assets/scss/_variables";

.page-agent {
    height: 100%;
    margin: 0 !important;
    padding: 20px;
    padding-bottom: 10px;
    box-sizing: border-box;
    overflow: hidden;
    display: flex;
    flex-direction: column;

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
        min-height: 120px;
        border: 2px solid transparent;
        box-sizing: border-box;

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

    .wrapper {
        display: flex;
        flex-grow: 1;
        overflow: hidden;
        padding: 5px;
        margin-left: -5px;
        margin-right: -5px;

        .sidebar {
            box-sizing: border-box;
            padding-right: var(--size-3);
            min-width: 250px;
            max-width: 250px;
            max-height: 100vh;

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

                &::before {
                    content: "";
                    display: block;
                    width: 6px;
                    height: 60%;
                    background: #6996e0;
                    position: absolute;
                    top: 20%;
                    left: 0;
                    opacity: 0;
                    transform: translateX(-100%);
                    transition: all 0.5s;
                }

                &:hover {
                    &::after {
                        width: 100%;
                        opacity: 0.3;
                    }
                }

                &.active {
                    &::before {
                        opacity: 1;
                        transform: translateX(0);
                    }
                }
            }
        }

        .main-content {
            padding: var(--size-5);
            flex-grow: 1;
            overflow: hidden;
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

        .wrapper {
            .sidebar {
                padding: var(--size-3);

                .close-btn {
                    display: block;
                }

                margin: 0;
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
}
</style>
