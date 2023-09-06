<template>
    <div class="page-agents flex column">
        <div class="contacts-root box grow flex gaps justify-center">
            <div class="card-base card-shadow--small search-card scrollable only-y">
                <h1 class="mt-0">Agents</h1>

                <el-input prefix-icon="el-icon-search" placeholder="Search a contact" clearable v-model="textFilter"> </el-input>

                <div class="o-050 text-right mt-10 mb-30">
                    <strong>{{ agentsFiltered.length }}</strong> Agents
                </div>

                <el-button @click="syncAgents()">
                    <i class="mdi mdi-account-plus mr-10"></i>
                    Sync Agents</el-button
                >

                <div class="p-20">
                    <p>Critical Assets</p>
                    <ul class="contacts-favourites">
                        <li v-for="agent in agentsCritical" :key="agent.agent_id">
                            <img :src="'/static/images/gallery/computer.png'" alt="user favourite avatar" />
                            <span>{{ agent.hostname }}</span>
                        </li>
                    </ul>
                    <p>Online Assets</p>
                    <ul class="contacts-favourites">
                        <li v-for="agent in agentsCritical" :key="agent.agent_id">
                            <img :src="'/static/images/gallery/computer.png'" alt="user favourite avatar" />
                            <span>{{ agent.hostname }}</span>
                        </li>
                    </ul>
                </div>
            </div>
            <div class="agents-list box grow scrollable only-y">
                <AgentCard v-for="agent in agentsFiltered" :key="agent.agent_id" :agent="agent" show-actions />
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed, onBeforeMount, ref } from "vue"
import { Agent } from "@/types/agents.d"
import { ElMessage } from "element-plus"
import AgentCard from "@/components/agents/AgentCard.vue"
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

function getAgents() {
    loadingAgents.value = true

    Api.agents
        .getAgents()
        .then(res => {
            if (res.data.success) {
                agents.value = res.data.agents
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

    .search-card {
        padding: 50px;
        max-width: 350px;
        //max-height: 320px;
        box-sizing: border-box;
        margin-bottom: 15px;

        .el-input,
        .el-button {
            width: 100%;
        }

        .contacts-favourites {
            margin: 0;
            padding: 0;
            list-style: none;
            overflow: auto;

            li {
                list-style: none;
                padding: 0;
                margin: 0;
                margin-right: 10px;
                margin-bottom: 10px;
                float: left;
                cursor: pointer;
                background: $background-color;
                color: $text-color-primary;
                border-radius: 4px;
                overflow: hidden;

                &:hover {
                    color: $text-color-accent;
                }

                img {
                    width: 30px;
                    height: 30px;
                    float: left;
                }

                span {
                    line-height: 30px;
                    padding: 0 10px;
                }
            }
        }
    }

    .search-wrap {
        margin: 0 auto;
        margin-bottom: 10px;
        padding: 0px 30px;
        box-sizing: border-box;
        width: 100%;
        max-width: 600px;

        i {
            display: inline-block;
            width: 22px;
        }

        input {
            outline: none;
            background: transparent;
            border: none;
            font-size: 15px;
            position: relative;
            top: -2px;
            width: 100%;
            padding: 0;
            color: $text-color-primary;
        }

        .contacts-tot {
            margin-right: 20px;
            margin-left: 10px;
        }

        a {
            border-bottom: 1px solid;
            text-decoration: none;
            color: $text-color-primary;

            &:hover {
                opacity: 0.6;
            }
        }
    }

    .contacts-root {
        max-height: 100%;
    }

    .agents-list {
        padding: 0px 30px;
        box-sizing: border-box;

        .agent-card {
            margin-bottom: 10px;
        }
    }

    .contacts-root {
        &.medium {
            .search-card {
                padding: 20px;
                max-width: 260px;
                //max-height: 260px;
            }
        }
        &.small {
            overflow-y: auto;
            display: block;
            -webkit-box-orient: vertical;
            -webkit-box-direction: normal;
            -ms-flex-direction: column;
            flex-direction: column;
            padding: 5px;

            .search-card {
                padding: 20px;
                max-width: 100%;
                width: 100%;
                //max-height: 240px;
                flex: none;
                -webkit-box-flex: none;
                -ms-flex: none;
                display: block;
                overflow: hidden !important;
            }

            .agents-list {
                flex: none;
                -webkit-box-flex: none;
                -ms-flex: none;
                display: block;
                overflow: hidden !important;
            }
        }
    }
}

@media (max-width: 768px) {
    .page-agents {
        .search-wrap {
            padding: 0;
        }
        .agents-list {
            padding: 0px;

            .contact {
                .avatar {
                    width: 40px;

                    img {
                        width: 40px;
                        height: 40px;
                    }
                }

                .info {
                    .phone {
                        display: none;
                    }

                    .name {
                        .phone {
                            display: block;
                        }
                    }
                }

                &:hover {
                    margin: 15px 0px;

                    .avatar {
                        width: 60px;

                        img {
                            width: 60px;
                            height: 60px;
                        }
                    }
                }
            }
        }

        .contacts-root {
            &.medium {
                .agents-list {
                    padding: 0 30px;
                }
            }
            &.small {
                .agents-list {
                    padding: 8px;
                }
            }
        }
    }
}
</style>
