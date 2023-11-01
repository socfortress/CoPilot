<template>
	<div class="page">
		<div class="mb-4">
			<n-button secondary type="primary" @click="showRulesDrawer = true">
				<template #icon>
					<Icon :name="RulesIcon" :size="22"></Icon>
				</template>
				View All Rules
			</n-button>
		</div>
		<n-card>
			<n-spin :show="loading">
				<n-collapse v-model:expanded-names="selectedPipeline" accordion>
					<n-collapse-item :title="pipe.title" :name="pipe.id" v-for="pipe of pipelines" :key="pipe.id">
						<template #header>
							<PipeTitle :pipeline="pipe" />
						</template>
						<template #header-extra>
							<n-button size="small" @click.stop="openModal(pipe)">
								<template #icon>
									<Icon :name="InfoIcon"></Icon>
								</template>
							</n-button>
						</template>
						<div class="overflow-hidden">
							<PipeDetails :pipeline="pipe" @click-rule="openRule($event)" />
						</div>
					</n-collapse-item>
				</n-collapse>
			</n-spin>
		</n-card>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			content-style="padding:0px"
			:style="{ maxWidth: 'min(600px, 90vw)', overflow: 'hidden' }"
			:title="highlightPipe?.title"
			:bordered="false"
			segmented
		>
			<PipeInfo :pipeline="highlightPipe" />
		</n-modal>

		<n-drawer
			v-model:show="showRulesDrawer"
			:width="700"
			style="max-width: 90vw"
			:trap-focus="false"
			display-directive="show"
		>
			<n-drawer-content closable body-content-style="padding:0">
				<template #header>
					<span>Rules list</span>
					<span class="font-mono ml-2 opacity-60" v-if="rulesTotal !== null">{{ rulesTotal }}</span>
				</template>
				<RulesList @loaded="rulesTotal = $event.total" :highlight="highlightRule" />
			</n-drawer-content>
		</n-drawer>
	</div>
</template>

<script setup lang="ts">
import { useMessage, NCollapse, NCollapseItem, NSpin, NButton, NModal, NCard, NDrawer, NDrawerContent } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import type { PipelineFull } from "@/types/graylog/pipelines.d"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import PipeDetails from "@/components/graylog/Pipelines/PipeDetails.vue"
import PipeInfo from "@/components/graylog/Pipelines/PipeInfo.vue"
import PipeTitle from "@/components/graylog/Pipelines/PipeTitle.vue"
import RulesList from "@/components/graylog/Pipelines/RulesList.vue"
import { watch } from "vue"

const RulesIcon = "ic:outline-swipe-right-alt"
const InfoIcon = "carbon:information"

const message = useMessage()
const showDetails = ref(false)
const loading = ref(false)
const pipelines = ref<PipelineFull[]>([])
const selectedPipeline = ref<string | null>(null)
const highlightPipe = ref<PipelineFull | undefined>(undefined)
const highlightRule = ref<string | null>(null)
const showRulesDrawer = ref(false)
const rulesTotal = ref<null | number>(null)

function openRule(id: string) {
	highlightRule.value = id
	showRulesDrawer.value = true
}

function setHighlightPipe(pipeline: PipelineFull) {
	highlightPipe.value = pipeline
}

function openModal(pipeline: PipelineFull) {
	setHighlightPipe(pipeline)
	showDetails.value = true
}

function getPipelines() {
	loading.value = true

	Api.graylog
		.getPipelinesFull()
		.then(res => {
			if (res.data.success) {
				pipelines.value = res.data.pipelines || []
				if (pipelines.value.length && !selectedPipeline.value) {
					selectedPipeline.value = pipelines.value[0].id
				}
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

watch(showRulesDrawer, val => {
	if (!val) {
		highlightRule.value = null
	}
})

onBeforeMount(() => {
	getPipelines()
})
</script>
