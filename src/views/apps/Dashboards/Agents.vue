<template>
    <div class="page-agents flex column">
        <div class="wrapper box grow flex justify-center">
            <AgentToolbar
                v-model="textFilter"
                :syncing="loadingSync"
                :agents-length="agents.length"
                :agents-filtered-length="agentsFiltered.length"
                :agents-critical="agentsCritical"
                :agents-online="agentsOnline"
                @sync="syncAgents()"
                @click="gotoAgentPage"
            />
            <transition-group class="agents-list box grow scrollable only-y" tag="div" name="list" v-loading="loadingAgents">
                <AgentCard
                    v-for="agent in agentsFiltered"
                    :key="agent.agent_id"
                    :agent="agent"
                    show-actions
                    @click="gotoAgentPage(agent)"
                />
            </transition-group>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed, onBeforeMount, ref } from "vue"
import { Agent } from "@/types/agents.d"
import { ElMessage } from "element-plus"
import AgentCard from "@/components/agents/AgentCard.vue"
import AgentToolbar from "@/components/agents/AgentToolbar.vue"
import { isAgentOnline } from "@/components/agents/utils"
import Api from "@/api"

const loadingAgents = ref(false)
const loadingSync = ref(false)
const agents = ref<Agent[]>([])
const textFilter = ref("")

const agentsFiltered = computed(() => {
    return agents.value.filter(
        ({ hostname, ip_address, agent_id, label }) =>
            (hostname + ip_address + agent_id + label).toString().toLowerCase().indexOf(textFilter.value.toString().toLowerCase()) !== -1
    )
})

const agentsCritical = computed(() => {
    return agents.value.filter(({ critical_asset }) => critical_asset)
})

const agentsOnline = computed(() => {
    return agents.value.filter(({ online }) => online)
})

function gotoAgentPage(agent: Agent) {
    console.log("goto", agent)
}

function getAgents() {
    loadingAgents.value = true

    Api.agents
        .getAgents()
        .then(res => {
            if (res.data.success) {
                agents.value = (res.data.agents || []).map(o => {
                    o.online = isAgentOnline(o.last_seen)
                    return o
                })
            } else {
                ElMessage({
                    message: res.data?.message || "An error occurred. Please try again later.",
                    type: "error"
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
            loadingAgents.value = false
        })
}
function syncAgents() {
    loadingSync.value = true

    Api.agents
        .getAgents()
        .then(res => {
            if (res.data.success) {
                ElMessage({
                    message: "Agents Synced Successfully",
                    type: "success"
                })
                getAgents()
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
                    message: err.response?.data?.message || "Sync returned Unauthorized.",
                    type: "error"
                })
            } else {
                ElMessage({
                    message: err.response?.data?.message || "Failed to Sync Agents",
                    type: "error"
                })
            }
        })
        .finally(() => {
            loadingSync.value = false
        })
}

onBeforeMount(() => {
    getAgents()
    syncAgents()
})
</script>

<style lang="scss" scoped>
@import "../../../assets/scss/_variables";

.page-agents {
    height: 100%;
    margin: 0 !important;
    padding: 20px;
    padding-bottom: 10px;
    box-sizing: border-box;
    container-type: inline-size;

    .wrapper {
        max-height: 100%;
        gap: var(--size-2);
    }

    .agents-list {
        padding: 0 5px;
        .agent-card {
            margin-bottom: var(--size-2);
        }

        .list-enter-active,
        .list-leave-active,
        .list-move {
            transition: 500ms cubic-bezier(0.59, 0.12, 0.34, 0.95);
            transition-property: opacity, transform;
        }

        .list-enter {
            opacity: 0;
            transform: scaleY(0);
        }

        .list-enter-to {
            opacity: 1;
            transform: scaleY(1);
        }

        .list-leave-active {
            position: absolute;
            left: 0;
            right: 0;
        }

        .list-leave-to {
            opacity: 0;
            transform: scaleY(0);
            transform-origin: center top;
        }
    }

    @container (max-width: 770px) {
        .wrapper {
            flex-direction: column;

            .agents-list {
                margin-left: -5px;
                margin-right: -10px;
            }
        }
    }
}
</style>
