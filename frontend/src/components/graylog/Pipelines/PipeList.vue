<template>
	<div class="pipe-list">
		<n-card content-class="!px-0">
			<n-spin :show="loading" content-class="min-h-7">
				<n-collapse v-if="pipelines.length" v-model:expanded-names="selectedPipeline" accordion>
					<n-collapse-item
						v-for="pipe of pipelines"
						:key="pipe.id"
						:title="pipe.title"
						:name="pipe.id"
						class="px-5"
					>
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
							<PipeDetails :pipeline="pipe" @click-rule="emit('openRule', $event)" />
						</div>
					</n-collapse-item>
				</n-collapse>
				<template v-else>
					<n-empty v-if="!loading" description="No pipelines found" class="h-32 justify-center" />
				</template>
			</n-spin>
		</n-card>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			content-class="!p-0"
			:style="{ maxWidth: 'min(600px, 90vw)', overflow: 'hidden' }"
			:title="highlightPipe?.title"
			:bordered="false"
			segmented
		>
			<PipeInfo :pipeline="highlightPipe" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { PipelineFull } from "@/types/graylog/pipelines.d"
import { NButton, NCard, NCollapse, NCollapseItem, NEmpty, NModal, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import PipeDetails from "@/components/graylog/Pipelines/PipeDetails.vue"
import PipeInfo from "@/components/graylog/Pipelines/PipeInfo.vue"
import PipeTitle from "@/components/graylog/Pipelines/PipeTitle.vue"

const emit = defineEmits<{
	(e: "openRule", value: string): void
}>()

const InfoIcon = "carbon:information"

const message = useMessage()
const showDetails = ref(false)
const loading = ref(false)
const pipelines = ref<PipelineFull[]>([])
const selectedPipeline = ref<string | null>(null)
const highlightPipe = ref<PipelineFull | undefined>(undefined)
const highlightRule = ref<string | null>(null)
const showRulesDrawer = ref(false)

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
	// MOCK
	/*
	pipelines.value = pipeline_full
	*/
})
</script>
