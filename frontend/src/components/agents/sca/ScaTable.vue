<template>
	<n-spin class="sca-table" :show="loading">
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
							<div class="flex items-center gap-2">
								<n-tooltip trigger="hover">
									<template #trigger>
										<n-button size="small" @click="showScaDetails(item)">
											<template #icon>
												<Icon :name="InfoIcon"></Icon>
											</template>
										</n-button>
									</template>
									Details
								</n-tooltip>

								<n-tooltip trigger="hover">
									<template #trigger>
										<n-button size="small" :loading="item.downloading" @click="scaDownload(item)">
											<template #icon>
												<Icon :name="DownloadIcon"></Icon>
											</template>
										</n-button>
									</template>
									Download CSV
								</n-tooltip>
							</div>
						</td>
						<td>
							<div class="flex flex-col gap-1">
								<strong>{{ item.policy_id }}</strong>

								<p class="hidden lg:flex">
									{{ item.extract }}

									<n-popover
										v-if="item.description !== item.extract"
										placement="top-end"
										content-class="max-w-96"
										scrollable
										to="body"
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
		<n-empty v-if="!loading && !scaList.length" description="No items found" class="justify-center h-48" />

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
import type { Agent, AgentSca } from "@/types/agents.d"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import { saveAs } from "file-saver"
import _truncate from "lodash/truncate"
import { NButton, NEmpty, NModal, NPopover, NScrollbar, NSpin, NTable, NTooltip, useMessage } from "naive-ui"
import { onBeforeMount, ref, toRefs } from "vue"
import ScaItem from "./ScaItem.vue"

interface SCAExt extends AgentSca {
	end_scan_text?: string
	extract?: string
	downloading: boolean
}

const props = defineProps<{
	agent: Agent
}>()
const { agent } = toRefs(props)

const DownloadIcon = "carbon:document-download"
const InfoIcon = "carbon:information"
const message = useMessage()
const loading = ref(false)
const showDetails = ref(false)
const scaList = ref<SCAExt[]>([])
const dFormats = useSettingsStore().dateFormat
const selectedSca = ref<SCAExt | null>(null)

function getSCA(agentId: string) {
	loading.value = true

	Api.agents
		.getSCA(agentId)
		.then(res => {
			if (res.data.success) {
				scaList.value = (res.data.sca || []).map(o => {
					return {
						...o,
						downloading: false,
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

function scaDownload(sca: SCAExt) {
	sca.downloading = true

	const fileName = `sca-${sca.policy_id}_${new Date().getTime()}.csv`

	Api.agents
		.scaResultsDownload(agent.value.agent_id, sca.policy_id)
		.then(res => {
			if (res.data) {
				saveAs(new Blob([res.data], { type: "text/csv;charset=utf-8" }), fileName)
			} else {
				message.warning("An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			sca.downloading = false
		})
}

onBeforeMount(() => {
	if (agent?.value?.agent_id) getSCA(agent.value.agent_id)
})
</script>
