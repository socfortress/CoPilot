<template>
	<n-spin class="sca-section" :show="loading">
		<n-scrollbar x-scrollable style="width: 100%">
			<n-table :bordered="true" class="min-w-max">
				<thead>
					<tr>
						<th></th>
						<th>Policy</th>
						<th>End scan</th>
						<th>Passed</th>
						<th>Failed</th>
						<th>Total checks</th>
						<th>Score</th>
					</tr>
				</thead>
				<tbody>
					<tr v-for="item of scaList" :key="item.policy_id">
						<td class="w-6">
							<n-button size="small" @click="showScaDetails(item)">
								<template #icon><Icon :name="InfoIcon"></Icon></template>
							</n-button>
						</td>
						<td>
							<div class="flex flex-col gap-1">
								<strong>{{ item.policy_id }}</strong>

								<p class="hidden lg:flex">
									{{ item.extract }}

									<n-popover
										placement="top-end"
										content-class="max-w-96"
										scrollable
										to="body"
										v-if="item.description !== item.extract"
									>
										<template #trigger>
											<span class="cursor-help underline">...</span>
										</template>
										<div class="flex flex-col py-2 px-1">
											{{ item.description }}
										</div>
									</n-popover>
								</p>
							</div>
						</td>
						<td>
							{{ item.end_scan_text }}
						</td>
						<td>
							{{ item.pass }}
						</td>
						<td>
							{{ item.fail }}
						</td>
						<td>
							{{ item.total_checks }}
						</td>
						<td>{{ item.score }}%</td>
					</tr>
				</tbody>
			</n-table>
		</n-scrollbar>
		<n-empty description="No items found" class="justify-center h-48" v-if="!loading && !scaList.length" />

		<n-modal
			v-model:show="showDetails"
			preset="card"
			:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(400px, 90vh)', overflow: 'hidden' }"
			:title="selectedSca?.policy_id || ''"
			:bordered="false"
			segmented
			content-class="!p-0"
		>
			<ScaItem v-if="selectedSca" :sca="selectedSca" :agent></ScaItem>
		</n-modal>
	</n-spin>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, toRefs } from "vue"
import Api from "@/api"
import { type Agent, type AgentSca } from "@/types/agents.d"
import { useMessage, NSpin, NEmpty, NScrollbar, NTable, NButton, NPopover, NModal } from "naive-ui"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import Icon from "@/components/common/Icon.vue"
import _truncate from "lodash/truncate"
import ScaItem from "./ScaItem.vue"

interface SCAExt extends AgentSca {
	end_scan_text?: string
	extract?: string
}

const props = defineProps<{
	agent: Agent
}>()
const { agent } = toRefs(props)

const InfoIcon = "carbon:information"
const message = useMessage()
const loading = ref(false)
const showDetails = ref(false)
const scaList = ref<SCAExt[]>([])
const dFormats = useSettingsStore().dateFormat
const selectedSca = ref<SCAExt | null>(null)

function getSCA(id: string) {
	loading.value = true

	Api.agents
		.getSCA(id)
		.then(res => {
			if (res.data.success) {
				scaList.value = (res.data.sca || []).map(o => {
					return {
						...o,
						end_scan_text: formatDate(o.end_scan, dFormats.datetime).toString(),
						extract: _truncate(o.description, {
							length: 50,
							omission: ""
						})
					}
				})
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

function showScaDetails(sca: SCAExt) {
	showDetails.value = true
	selectedSca.value = sca
}

onBeforeMount(() => {
	if (agent?.value?.agent_id) getSCA(agent.value.agent_id)
})
</script>

<style lang="scss" scoped>
.sca-section {
	container-type: inline-size;
	min-height: 100px;

	.group {
		@apply gap-4;
		width: 100%;
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(175px, 1fr));
		grid-auto-flow: row dense;
	}

	@container (max-width: 500px) {
		.group {
			grid-template-columns: repeat(auto-fit, 100%);
		}
	}
}
</style>
