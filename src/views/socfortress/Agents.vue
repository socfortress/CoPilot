<template>
	<div class="page page-wrapped flex flex-col page-without-footer">
		<div class="wrapper flex grow gap-4">
			<div class="sidebar">
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
			</div>
			<div class="main grow flex flex-col overflow-hidden">
				<n-spin class="w-full h-full overflow-hidden flex flex-col" :show="loadingAgents">
					<n-scrollbar class="grow">
						<div class="agents-list flex flex-grow flex-col gap-3">
							<AgentCard
								v-for="agent in agentsFiltered"
								:key="agent.agent_id"
								:agent="agent"
								show-actions
								@delete="syncAgents()"
								@click="gotoAgentPage(agent)"
							/>
						</div>
					</n-scrollbar>
				</n-spin>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeMount, ref, watch } from "vue"
import { type Agent } from "@/types/agents.d"
import AgentCard from "@/components/agents/AgentCard.vue"
import AgentToolbar from "@/components/agents/AgentToolbar.vue"
import { isAgentOnline } from "@/components/agents/utils"
import Api from "@/api"
import { useRouter } from "vue-router"
import { useMessage, NSpin, NScrollbar } from "naive-ui"
import _debounce from "lodash/debounce"

const message = useMessage()
const router = useRouter()
const loadingAgents = ref(false)
const loadingSync = ref(false)
const agents = ref<Agent[]>([])
const textFilter = ref("")

const textFilterDebounced = ref("")

const update = _debounce(value => {
	textFilterDebounced.value = value
}, 100)

watch(textFilter, val => {
	update(val)
})

const agentsFiltered = computed(() => {
	return agents.value.filter(
		({ hostname, ip_address, agent_id, label }) =>
			(hostname + ip_address + agent_id + label)
				.toString()
				.toLowerCase()
				.indexOf(textFilterDebounced.value.toString().toLowerCase()) !== -1
	)
})

const agentsCritical = computed(() => {
	return agents.value.filter(({ critical_asset }) => critical_asset)
})

const agentsOnline = computed(() => {
	return agents.value.filter(({ online }) => online)
})

function gotoAgentPage(agent: Agent) {
	router.push(`/agent/${agent.agent_id}`).catch(err => {})
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
				message.error(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingAgents.value = false
		})
}

function syncAgents() {
	loadingSync.value = true

	Api.agents
		.syncAgents()
		.then(res => {
			if (res.data.success) {
				message.success("Agents Synced Successfully")
				getAgents()
			} else {
				message.error("An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			if (err.response.status === 401) {
				message.error(err.response?.data?.message || "Sync returned Unauthorized.")
			} else {
				message.error(err.response?.data?.message || "Failed to Sync Agents")
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
.page {
	container-type: inline-size;

	.wrapper {
		position: relative;
		height: 100%;
		overflow: hidden;

		.sidebar {
			.agent-toolbar {
				height: 100%;
			}
		}

		:deep() {
			.n-spin-content {
				overflow: hidden;
				max-height: 100%;
			}
		}

		.main {
			:deep() {
				.n-scrollbar > .n-scrollbar-rail.n-scrollbar-rail--vertical {
					right: 0;
				}
			}
		}

		.agents-list {
			width: 100%;
		}
	}
	@container (max-width: 770px) {
		.wrapper {
			flex-direction: column;
		}
	}
}
</style>
