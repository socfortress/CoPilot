<template>
	<slot :open-evaluation />

	<n-modal
		v-model:show="showDetails"
		preset="card"
		content-class="!p-0"
		:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(550px, 90vh)' }"
		:title="`Evaluation: ${processName}`"
		:bordered="false"
		segmented
	>
		<n-spin :show="loading" class="min-h-48">
			<n-tabs v-if="evaluation" type="line" animated :tabs-padding="24">
				<n-tab-pane
					name="Overview"
					tab="Overview"
					display-directive="show:lazy"
					class="flex flex-col gap-4 !py-8"
				>
					<div class="px-7">
						<n-card content-class="bg-secondary-color" class="overflow-hidden">
							<div class="flex justify-between gap-8 flex-wrap">
								<n-statistic label="Rank" :value="evaluation.rank" tabular-nums />
								<n-statistic label="EPS" :value="eps" tabular-nums />
								<n-statistic label="Host Prevalence" :value="`${evaluation.host_prev}%`" tabular-nums />
							</div>
						</n-card>
					</div>

					<div class="px-7">
						{{ evaluation.description }}
					</div>
				</n-tab-pane>
				<n-tab-pane name="Intel" tab="Intel" display-directive="show:lazy">
					<div class="p-7 pt-4">
						<n-input
							:value="evaluation.intel"
							type="textarea"
							readonly
							placeholder="Empty"
							size="large"
							:autosize="{
								minRows: 3,
								maxRows: 18,
							}"
						/>
					</div>
				</n-tab-pane>
				<n-tab-pane name="Hashes" tab="Hashes" display-directive="show:lazy">
					<ListPercentage
						class="p-7 pt-4"
						:list="evaluation.hashes"
						label-key="hash"
						percentage-key="percentage"
					/>
				</n-tab-pane>
				<n-tab-pane name="Network" tab="Network" display-directive="show:lazy">
					<ListPercentage
						class="p-7 pt-4"
						:list="evaluation.network"
						label-key="port"
						percentage-key="usage"
					/>
				</n-tab-pane>
				<n-tab-pane name="Parents" tab="Parents" display-directive="show:lazy">
					<ListPercentage
						class="p-7 pt-4"
						:list="evaluation.parents"
						label-key="name"
						percentage-key="percentage"
					/>
				</n-tab-pane>
				<n-tab-pane name="Paths" tab="Paths" display-directive="show:lazy">
					<ListPercentage
						class="p-7 pt-4"
						:list="evaluation.paths"
						label-key="directory"
						percentage-key="percentage"
					/>
				</n-tab-pane>
			</n-tabs>
			<n-empty v-if="!loading && !evaluation" description="Evaluation not found" class="justify-center h-48" />
		</n-spin>
	</n-modal>
</template>

<script setup lang="ts">
import type { EvaluationData } from "@/types/threatIntel.d"
import Api from "@/api"
import _toSafeInteger from "lodash/toSafeInteger"
import { NCard, NEmpty, NInput, NModal, NSpin, NStatistic, NTabPane, NTabs, useMessage } from "naive-ui"
import { computed, defineAsyncComponent, ref } from "vue"

const { processName } = defineProps<{
	processName: string
}>()

const ListPercentage = defineAsyncComponent(() => import("@/components/common/ListPercentage.vue"))

const evaluation = ref<EvaluationData | null>(null)
const showDetails = ref<boolean>(false)
const loading = ref<boolean>(false)
const message = useMessage()

const eps = computed(() => _toSafeInteger(evaluation.value?.eps || 0))

function openEvaluation() {
	if (!evaluation.value) {
		getEvaluation()
	}
	showDetails.value = true
}

function getEvaluation() {
	loading.value = true

	Api.threatIntel
		.processNameEvaluation(processName)
		.then(res => {
			if (res.data.success) {
				evaluation.value = res.data?.data || null
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
</script>
