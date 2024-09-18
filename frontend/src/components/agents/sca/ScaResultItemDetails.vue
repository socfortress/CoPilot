<template>
	<n-tabs type="line" animated :tabs-padding="24">
		<n-tab-pane name="Overview" tab="Overview" display-directive="show:lazy" class="flex flex-col gap-4 !py-8">
			<div class="px-7">
				<n-card content-class="bg-secondary-color" class="overflow-hidden">
					<div class="flex justify-between gap-8 flex-wrap">
						<n-statistic label="Result" tabular-nums>
							<span
								class="uppercase"
								:class="
									data.result === 'failed'
										? 'text-error-color'
										: data.result === 'not applicable'
											? 'text-warning-color'
											: 'text-success-color'
								"
							>
								{{ data.result }}
							</span>
						</n-statistic>
						<n-statistic label="Condition" tabular-nums>
							<span class="uppercase">{{ data.condition }}</span>
						</n-statistic>
						<n-statistic label="Compliance" :value="data.compliance.length" tabular-nums />
						<n-statistic label="Rules" :value="data.rules.length" tabular-nums />
					</div>
				</n-card>
			</div>

			<div class="px-7">
				<n-card content-class="bg-secondary-color !p-0" class="overflow-hidden">
					<div
						v-shiki="{ lang: 'shell', decode: true }"
						class="scrollbar-styled overflow-hidden code-bg-transparent"
					>
						<pre v-html="data.command"></pre>
					</div>
				</n-card>
			</div>

			<div v-if="properties" class="grid gap-2 grid-auto-fit-200 px-7">
				<KVCard v-for="(value, key) of properties" :key="key">
					<template #key>
						{{ key }}
					</template>
					<template #value>
						{{ value ?? "-" }}
					</template>
				</KVCard>
			</div>
		</n-tab-pane>
		<n-tab-pane name="Description" tab="Description" display-directive="show:lazy">
			<div class="p-7 pt-4">
				<n-input
					:value="data.description"
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
		<n-tab-pane name="Rationale" tab="Rationale" display-directive="show:lazy">
			<div class="p-7 pt-4">
				<n-input
					:value="data.rationale"
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
		<n-tab-pane name="Reason" tab="Reason" display-directive="show:lazy">
			<div class="p-7 pt-4">
				<n-input
					:value="data.reason"
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
		<n-tab-pane name="Remediation" tab="Remediation" display-directive="show:lazy">
			<div class="p-7 pt-4">
				<n-input
					:value="data.remediation"
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
		<n-tab-pane name="Compliance" tab="Compliance" display-directive="show:lazy">
			<div class="p-7 pt-4 flex flex-col gap-1">
				<n-card
					v-for="item of data.compliance"
					:key="item.key"
					content-class="bg-secondary-color flex flex-col gap-2"
					class="overflow-hidden"
					size="small"
				>
					<div>{{ item.key }}</div>
					<p>{{ item.value }}</p>
				</n-card>
			</div>
		</n-tab-pane>
		<n-tab-pane name="Rules" tab="Rules" display-directive="show:lazy">
			<div class="p-7 pt-4 flex flex-col gap-1">
				<n-card
					v-for="item of data.rules"
					:key="item.type + item.rule"
					content-class="bg-secondary-color flex flex-col gap-2"
					class="overflow-hidden"
					size="small"
				>
					<div>{{ item.type }}</div>
					<p>{{ item.rule }}</p>
				</n-card>
			</div>
		</n-tab-pane>
	</n-tabs>
</template>

<script setup lang="ts">
import type { ScaPolicyResult } from "@/types/agents.d"
import KVCard from "@/components/common/KVCard.vue"
import vShiki from "@/directives/v-shiki"
import _pick from "lodash/pick"
import { NCard, NInput, NStatistic, NTabPane, NTabs } from "naive-ui"
import { computed } from "vue"

const { data } = defineProps<{
	data: ScaPolicyResult
}>()

const properties = computed(() => {
	return _pick(data, ["id", "policy_id", "title"])
})
</script>
