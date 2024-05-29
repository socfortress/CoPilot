<template>
	<n-tabs type="line" animated :tabs-padding="24">
		<n-tab-pane name="Details" tab="Details" display-directive="show" class="flex flex-col gap-4 !py-8">
			<div class="px-7">
				<n-card content-class="bg-secondary-color" class="overflow-hidden">
					<div class="flex justify-between gap-8 flex-wrap">
						<n-statistic label="Checks" :value="sca.total_checks" tabular-nums />
						<n-statistic label="Pass" :value="sca.pass" tabular-nums />
						<n-statistic label="Fail" :value="sca.fail" tabular-nums />
						<n-statistic label="Invalid" :value="sca.invalid" tabular-nums />
						<n-statistic label="Score" :value="sca.score + '%'" tabular-nums />
					</div>
				</n-card>
			</div>
			<div class="px-7">
				<n-card content-class="bg-secondary-color" class="overflow-hidden">
					<div class="flex justify-between gap-8 xs:!flex-row flex-col">
						<n-statistic
							class="grow"
							label="Start scan"
							:value="formatDate(sca.start_scan, dFormats.datetime).toString()"
						/>
						<n-statistic
							class="grow"
							label="End scan"
							:value="formatDate(sca.end_scan, dFormats.datetime).toString()"
						/>
					</div>
				</n-card>
			</div>
			<div class="grid gap-2 grid-auto-flow-200 px-7" v-if="properties">
				<KVCard v-for="(value, key) of properties" :key="key">
					<template #key>{{ key }}</template>
					<template #value>
						<template v-if="value && key === 'references'">
							<a
								:href="value"
								target="_blank"
								alt="references url"
								rel="nofollow noopener noreferrer"
								class="leading-6"
							>
								<span>
									{{ value }}
								</span>
								<Icon :name="LinkIcon" :size="14" class="relative top-0.5 ml-2" />
							</a>
						</template>
						<template v-else>
							{{ value ?? "-" }}
						</template>
					</template>
				</KVCard>
			</div>
		</n-tab-pane>
		<n-tab-pane name="Description" tab="Description" display-directive="show">
			<div class="p-7 pt-4">
				<n-input
					:value="sca.description"
					type="textarea"
					readonly
					placeholder="Empty"
					size="large"
					:autosize="{
						minRows: 3,
						maxRows: 18
					}"
				/>
			</div>
		</n-tab-pane>
		<n-tab-pane name="SCA Results" tab="SCA Results" display-directive="show:lazy">
			<div class="p-7 pt-4">
				<ScaResults :sca="sca" :agent />
			</div>
		</n-tab-pane>
	</n-tabs>
</template>

<script setup lang="ts">
import { NTabs, NTabPane, NInput, NStatistic, NCard } from "naive-ui"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import { type Agent, type AgentSca } from "@/types/agents.d"
import KVCard from "@/components/common/KVCard.vue"
import Icon from "@/components/common/Icon.vue"
import { computed } from "vue"
import ScaResults from "./ScaResults.vue"
import _pick from "lodash/pick"

const { sca, agent } = defineProps<{ sca: AgentSca; agent: Agent }>()

const dFormats = useSettingsStore().dateFormat
const LinkIcon = "carbon:launch"

const properties = computed(() => {
	return _pick(sca, ["name", "hash_file", "references"])
})
</script>
