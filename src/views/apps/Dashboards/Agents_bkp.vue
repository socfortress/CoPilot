<template>
    <div class="page-contacts flex column" id="page-contacts">
        <resize-observer @notify="__resizeHanlder" />

        <div class="contacts-root box grow flex gaps justify-center" :class="contactsClass">
            <div class="card-base card-shadow--small search-card scrollable only-y">
                <h1 class="mt-0">Agents</h1>

                <el-input prefix-icon="el-icon-search" placeholder="Search a contact" clearable v-model="search"> </el-input>

                <div class="o-050 text-right mt-10 mb-30">
                    <strong>{{ agentsFiltered.length }}</strong> Agents
                </div>

                <el-button @click="sync_agents({})">
                    <i class="mdi mdi-account-plus mr-10"></i>
                    Sync Agents</el-button
                >

                <div class="p-20">
                    <p>Critical Assets</p>
                    <ul class="contacts-favourites">
                        <li v-for="agent in agentsFavorite" :key="agent.agent_id" @click="openDialog(c)">
                            <img :src="'/static/images/gallery/computer.png'" alt="user favourite avatar" />
                            <span>{{ agent.hostname }}</span>
                        </li>
                    </ul>
                </div>
            </div>
            <div class="contacts-list box grow scrollable only-y">
                <div v-for="agent in agentsFiltered" :key="agent.agent_id" class="flex contact" @click="openEditAgentsModal(agent)">
                    <div class="star align-vertical p-10 fs-22">
                        <i class="mdi mdi-star align-vertical-middle" v-if="agent.critical_asset"></i>
                        <i class="mdi mdi-star-outline align-vertical-middle" v-if="!agent.critical_asset"></i>
                    </div>
                    <div class="avatar align-vertical">
                        <img :src="'/static/images/gallery/computer.png'" class="align-vertical-middle" alt="user avatar" />
                    </div>
                    <div class="info box grow flex">
                        <div class="name box grow flex column justify-center p-10">
                            <div class="fullname fs-18">
                                <strong>{{ agent.hostname }}</strong>
                            </div>
                            <div class="ip fs-14 secondary-text">{{ agent.ip_address }}</div>
                            <div class="os fs-14 secondary-text">{{ agent.os }}</div>
                            <div class="os fs-14 secondary-text">{{ agent.label }}</div>
                        </div>
                        <div class="phone align-vertical p-10">
                            <span class="align-vertical-middle">{{ agent.last_seen }}</span>
                        </div>
                        <!--Add a el-button to make the agent critical-->
                        <div class="phone align-vertical p-10">
                            <el-button type="primary" @click="makeAgentCritical(agent.agent_id)" v-if="!agent.critical_asset">
                                <i class="mdi mdi-star-outline align-vertical-middle"></i>
                            </el-button>
                            <el-button type="primary" @click="makeAgentUncritical(agent.agent_id)" v-if="agent.critical_asset">
                                <i class="mdi mdi-star align-vertical-middle"></i>
                            </el-button>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <user-dialog v-model="dialogvisible" :userdata="userdata"></user-dialog>
    </div>
</template>

<script>
import UserDialog from "@/components/UserDialog.vue"
import Contacts from "@/assets/data/CONTACTS_MOCK_DATA.json"
import { defineComponent } from "vue"
import _ from "lodash"
import ResizeObserver from "@/components/vue-resize/ResizeObserver.vue"
import axios from "axios"

export default defineComponent({
    name: "Contacts",
    data() {
        return {
            loading: false,
            agents: [],
            currentAgent: null,

            // Configure Modal
            isEditAgentsModalActive: false,

            search: "",
            dialogvisible: false,
            pageWidth: 0,
            userdata: {},
            contacts: Contacts.slice(0, 30)
        }
    },
    computed: {
        contactsFiltered() {
            return this.contacts.filter(
                ({ full_name, email, phone }) =>
                    (full_name + email + phone).toString().toLowerCase().indexOf(this.search.toString().toLowerCase()) !== -1
            )
        },
        contactsClass() {
            return this.pageWidth >= 870 ? "large" : this.pageWidth >= 760 ? "medium" : "small"
        },
        contactsFavourite() {
            return this.contacts.filter(({ starred }) => starred)
        },
        agentsFiltered() {
            return this.agents.filter(
                ({ agent_name, agent_ip, agent_id }) =>
                    (agent_name + agent_ip + agent_id).toString().toLowerCase().indexOf(this.search.toString().toLowerCase()) !== -1
            )
        },
        agentsFavorite() {
            return this.agents.filter(({ critical_asset }) => critical_asset)
        }
    },
    methods: {
        openEditAgentsModal(agent) {
            this.currentAgent = agent
            this.isEditAgentsModalActive = true
        },
        closeEditAgentsModal() {
            this.isEditAgentsModalActive = false
        },

        openDialog(data) {
            this.userdata = data
            this.dialogvisible = true
        },
        setPageWidth() {
            this.pageWidth = document.getElementById("page-contacts").offsetWidth
        },
        __resizeHanlder: _.throttle(function (e) {
            this.setPageWidth()
        }, 700),
        get_agents() {
            const path = "http://127.0.0.1:5000/agents"
            this.loading = true
            true,
                axios
                    .get(path)
                    .then(response => {
                        if (response.data.success && Array.isArray(response.data.agents)) {
                            this.agents = response.data.agents
                        } else {
                            console.error("Received non-array agents: ", response.data)
                            this.agents = [] // Reset to empty array
                        }
                    })
                    .catch(error => {
                        console.log(error)
                        this.loading = false
                    })
        },
        sync_agents() {
            const path = "http://127.0.0.1:5000/sync"
            this.loading = true
            true,
                axios
                    .get(path)
                    .then(response => {
                        this.sync = response.data
                        this.loading = false
                        this.succssMesaage = "Agents Synced Successfully"
                        this.$message({
                            message: this.succssMesaage,
                            type: "success"
                        })
                        this.get_agents()
                    })
                    .catch(error => {
                        if (error.response.status === 401) {
                            this.errorMessage = "Unauthorized"
                            this.$message({
                                message: this.errorMessage,
                                type: "error"
                            })
                        } else {
                            this.$message({
                                message: "Failed to Sync Agents",
                                type: "error"
                            })
                        }
                    })
        },
        makeAgentCritical(agent_id) {
            const path = "http://127.0.0.1:5000/agents/" + agent_id + "/critical"
            axios
                .put(path)
                .then(response => {
                    this.loading = false
                    this.succssMesaage = "Agent Criticality Updated Successfully"
                    this.$message({
                        message: this.succssMesaage,
                        type: "success"
                    })
                    this.get_agents()
                })
                .catch(error => {
                    if (error.response.status === 401) {
                        this.errorMessage = "Unauthorized"
                        this.$message({
                            message: this.errorMessage,
                            type: "error"
                        })
                    } else {
                        this.$message({
                            message: "Failed to Update Agent Criticality",
                            type: "error"
                        })
                    }
                })
        },
        makeAgentUncritical(agent_id) {
            const path = "http://127.0.0.1:5000/agents/" + agent_id + "/uncritical"
            axios
                .put(path)
                .then(response => {
                    this.loading = false
                    this.succssMesaage = "Agent Criticality Updated Successfully"
                    this.$message({
                        message: this.succssMesaage,
                        type: "success"
                    })
                    this.get_agents()
                })
                .catch(error => {
                    if (error.response.status === 401) {
                        this.errorMessage = "Unauthorized"
                        this.$message({
                            message: this.errorMessage,
                            type: "error"
                        })
                    } else {
                        this.$message({
                            message: "Failed to Update Agent Criticality",
                            type: "error"
                        })
                    }
                })
        }
    },
    mounted() {
        this.setPageWidth()
        this.get_agents()
    },
    watch: {
        agentsFiltered(newValue) {
            console.log("agentsFiltered:", newValue)
        }
    },
    components: {
        ResizeObserver,
        UserDialog
    }
})
</script>

<style lang="scss" scoped>
@import "../../../assets/scss/_variables";

.page-contacts {
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

    .contacts-list {
        //margin: 0 auto;
        width: 100%;
        max-width: 965px;
        padding: 0px 30px;
        box-sizing: border-box;

        .contact {
            margin: 10px 0;
            padding: 5px;
            box-sizing: border-box;
            cursor: pointer;
            transition: all 0.5s 0.25s;

            .star {
                .mdi-star {
                    color: #ffd730;
                }
                .mdi-star-outline {
                    opacity: 0.5;
                }
            }

            .avatar {
                width: 60px;
                transition: all 0.5s 0.25s;

                img {
                    border: 1px solid transparentize($text-color-primary, 0.9);
                    box-sizing: border-box;
                    width: 50px;
                    height: 50px;
                    border-radius: 50%;
                    transition: all 0.5s 0.25s;
                }
            }

            .info {
                word-break: break-word;

                .name {
                    //.fullname {}

                    .email {
                        opacity: 0;
                        line-height: 0;
                        transition: all 0.5s 0.25s;
                    }

                    .phone {
                        display: none;
                    }
                }

                //.phone {}
            }

            &:hover {
                margin: 15px -20px;
                padding: 10px;
                background-color: lighten($background-color, 20%);
                border-radius: 5px;
                box-shadow:
                    0 8px 16px 0 rgba(40, 40, 90, 0.09),
                    0 3px 6px 0 rgba(0, 0, 0, 0.065);

                .avatar {
                    width: 90px;

                    img {
                        width: 90px;
                        height: 90px;
                    }
                }

                .info {
                    .name {
                        .email {
                            opacity: 1;
                            line-height: 1.4;
                        }
                    }
                }
            }
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

            .contacts-list {
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
    .page-contacts {
        .search-wrap {
            padding: 0;
        }
        .contacts-list {
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
                .contacts-list {
                    padding: 0 30px;
                }
            }
            &.small {
                .contacts-list {
                    padding: 8px;
                }
            }
        }
    }
}
</style>
