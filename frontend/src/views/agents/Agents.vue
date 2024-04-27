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
					@click="gotoAgent($event.agent_id)"
				/>
			</div>
			<div class="main grow flex flex-col overflow-hidden">
				<n-spin class="w-full h-full overflow-hidden flex flex-col" :show="loadingAgents">
					<n-scrollbar class="grow">
						<div class="agents-list flex flex-grow flex-col gap-3">
							<template v-if="agentsFiltered.length">
								<AgentCard
									v-for="agent in itemsPaginated"
									:key="agent.agent_id"
									:agent="agent"
									show-actions
									@delete="syncAgents()"
									@click="gotoAgent(agent.agent_id)"
									class="item-appear item-appear-bottom item-appear-005"
								/>
							</template>
							<template v-else>
								<n-empty
									description="No items found"
									class="justify-center h-48"
									v-if="!loadingAgents"
								/>
							</template>
						</div>
					</n-scrollbar>
				</n-spin>

				<div class="pagination-wrapper">
					<n-pagination
						v-model:page="page"
						:page-size="pageSize"
						:page-slot="5"
						:item-count="agentsFiltered.length"
					/>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeMount, ref, watch } from "vue"
import { AgentStatus, type Agent } from "@/types/agents.d"
import AgentCard from "@/components/agents/AgentCard.vue"
import AgentToolbar from "@/components/agents/AgentToolbar.vue"
import Api from "@/api"
import { useMessage, NSpin, NScrollbar, NEmpty, NPagination } from "naive-ui"
import _debounce from "lodash/debounce"
import { useGoto } from "@/composables/useGoto"

const message = useMessage()
const { gotoAgent } = useGoto()
const loadingAgents = ref(false)
const loadingSync = ref(false)
const agents = ref<Agent[]>([])
const textFilter = ref("")
const page = ref(1)
const pageSize = ref(20)

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

const itemsPaginated = computed(() => {
	const from = (page.value - 1) * pageSize.value
	const to = page.value * pageSize.value

	return agentsFiltered.value.slice(from, to)
})

const agentsCritical = computed(() => {
	return agents.value.filter(({ critical_asset }) => critical_asset)
})

const agentsOnline = computed(() => {
	return agents.value.filter(({ wazuh_agent_status }) => wazuh_agent_status === AgentStatus.Active)
})

function getAgents() {
	loadingAgents.value = true

	Api.agents
		.getAgents()
		.then(res => {
			if (res.data.success) {
				agents.value = res.data.agents || []
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
			if (err.response?.status === 401) {
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
			position: relative;
			border-radius: var(--border-radius);

			:deep() {
				.n-scrollbar > .n-scrollbar-rail.n-scrollbar-rail--vertical {
					right: 0;
					bottom: 50px;
				}
			}

			.pagination-wrapper {
				--size: 10px;
				position: absolute;
				bottom: 0;
				right: 0;
				background-color: var(--bg-body);
				padding-left: var(--size);
				padding-top: var(--size);
				border-top-left-radius: var(--size);

				&::before,
				&::after {
					content: "";
					position: absolute;
					width: var(--size);
					height: var(--size);
					left: calc(var(--size) * -1);
					display: block;
					bottom: 0px;
					z-index: 1;
					background-image: radial-gradient(
						circle at 0 0,
						rgba(0, 0, 0, 0) calc(var(--size) - 1px),
						var(--bg-body) calc(var(--size) + 0px)
					);
				}

				&::after {
					bottom: initial;
					left: initial;
					top: calc(var(--size) * -1);
					right: 0;
				}
			}
		}

		.agents-list {
			width: 100%;

			.item-appear {
				&:last-child {
					margin-bottom: 50px;
				}
			}
		}
	}
	@container (max-width: 770px) {
		.wrapper {
			flex-direction: column;
		}
	}
}
</style>
