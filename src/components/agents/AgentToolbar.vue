<template>
    <div class="agent-toolbar">
        <div class="agents-header">
            <h2>Agents</h2>
            <el-button @click="emit('sync')" :loading="syncing">
                <i class="mdi mdi-account-sync-outline mr-2 fs-18" v-if="!syncing"></i>
                <span class="ml-6"> Sync Agents </span>
            </el-button>
        </div>

        <div class="agent-search">
            <el-input :prefix-icon="SearchIcon" placeholder="Search a contact" clearable v-model="textFilter"> </el-input>

            <div class="o-050 text-right mt-10 mb-30">
                <strong v-if="agentsFilteredLength !== agentsLength">{{ agentsFilteredLength }}</strong>
                <span class="mh-5" v-if="agentsFilteredLength !== agentsLength">/</span>
                <strong>{{ agentsLength }}</strong> Agents
            </div>
        </div>

        <div class="p-20">
            <p>Critical Assets</p>
            <ul class="contacts-favourites">
                <li v-for="agent in agentsCritical" :key="agent.agent_id" @click="emit('click', agent)">
                    <img :src="'/static/images/gallery/computer.png'" alt="user favourite avatar" />
                    <span>{{ agent.hostname }}</span>
                </li>
            </ul>
            <p>Online Assets</p>
            <ul class="contacts-favourites">
                <li v-for="agent in agentsOnline" :key="agent.agent_id" @click="emit('click', agent)">
                    <img :src="'/static/images/gallery/computer.png'" alt="user favourite avatar" />
                    <span>{{ agent.hostname }}</span>
                </li>
            </ul>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed, ref, toRefs } from "vue"
import { Agent } from "@/types/agents.d"
import dayjs from "dayjs"
import Api from "@/api"
import { ElMessage, ElMessageBox } from "element-plus"
import { Star as StarIcon, Search as SearchIcon } from "@element-plus/icons-vue"

const emit = defineEmits<{
    (e: "sync"): void
    (e: "update:modelValue", value: string): void
    (e: "click", value: Agent): void
}>()

const props = defineProps<{
    modelValue: string
    syncing?: boolean
    agentsLength?: number
    agentsFilteredLength?: number
    agentsCritical?: Agent[]
    agentsOnline?: Agent[]
}>()
const { modelValue, syncing, agentsLength, agentsFilteredLength, agentsCritical, agentsOnline } = toRefs(props)

const textFilter = computed<string>({
    get() {
        return modelValue.value
    },
    set(value) {
        emit("update:modelValue", value)
    }
})
</script>

<style lang="scss" scoped>
@import "@/assets/scss/_variables";
@import "@/assets/scss/card-shadow";

.agent-toolbar {
    container-type: inline-size;
    @extend .card-base;
    @extend .card-shadow--small;
    overflow: hidden;
    border: 2px solid transparent;
    max-width: 100%;
    min-width: 300px;
    padding: var(--size-3) var(--size-4);
    box-sizing: border-box;

    .agents-header {
        display: flex;
        align-items: center;
        justify-content: space-between;

        h2 {
            margin: 0;
        }
    }

    .agent-search {
        margin-top: var(--size-4);
    }

    @container (max-width: 550px) {
    }
}
</style>
