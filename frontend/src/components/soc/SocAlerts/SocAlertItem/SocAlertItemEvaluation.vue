<template>
	<code class="cursor-pointer text-primary-color" @click="openEvaluation()">
		{{ processName }}
		<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
	</code>

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
			<n-tabs type="line" animated :tabs-padding="24" v-if="evaluation">
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
								<n-statistic label="Host Prevalence" :value="evaluation.host_prev + '%'" tabular-nums />
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
								maxRows: 18
							}"
						/>
					</div>
				</n-tab-pane>
				<n-tab-pane name="Hashes" tab="Hashes" display-directive="show:lazy">
					<ListPercentage
						class="p-7 pt-4"
						:list="evaluation.hashes"
						labelKey="hash"
						percentageKey="percentage"
					/>
				</n-tab-pane>
				<n-tab-pane name="Network" tab="Network" display-directive="show:lazy">
					<ListPercentage class="p-7 pt-4" :list="evaluation.network" labelKey="port" percentageKey="usage" />
				</n-tab-pane>
				<n-tab-pane name="Parents" tab="Parents" display-directive="show:lazy">
					<ListPercentage
						class="p-7 pt-4"
						:list="evaluation.parents"
						labelKey="name"
						percentageKey="percentage"
					/>
				</n-tab-pane>
				<n-tab-pane name="Paths" tab="Paths" display-directive="show:lazy">
					<ListPercentage
						class="p-7 pt-4"
						:list="evaluation.paths"
						labelKey="directory"
						percentageKey="percentage"
					/>
				</n-tab-pane>
			</n-tabs>
			<n-empty description="Evaluation not found" class="justify-center h-48" v-if="!loading && !evaluation" />
		</n-spin>
	</n-modal>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import { useMessage, NModal, NSpin, NTabs, NTabPane, NStatistic, NInput, NCard, NEmpty } from "naive-ui"
import type { EvaluationData } from "@/types/threatIntel"
import { computed, defineAsyncComponent, ref } from "vue"
import Api from "@/api"
import _toSafeInteger from "lodash/toSafeInteger"
const ListPercentage = defineAsyncComponent(() => import("@/components/common/ListPercentage.vue"))

const { processName } = defineProps<{
	processName: string
}>()

const LinkIcon = "carbon:launch"
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
