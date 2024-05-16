<template>
	<div class="pipe-list">
		<n-card>
			<n-spin :show="loading">
				<n-collapse
					v-model:expanded-names="selectedPipeline"
					accordion
					:style="minHeight ? `min-height: ${minHeight}` : ''"
				>
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
							<PipeDetails :pipeline="pipe" @click-rule="emit('openRule', $event)" />
						</div>
					</n-collapse-item>
				</n-collapse>
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
import { useMessage, NCollapse, NCollapseItem, NSpin, NButton, NModal, NCard } from "naive-ui"
import { onBeforeMount, ref, toRefs, watch } from "vue"
import type { PipelineFull } from "@/types/graylog/pipelines.d"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import PipeDetails from "@/components/graylog/Pipelines/PipeDetails.vue"
import PipeInfo from "@/components/graylog/Pipelines/PipeInfo.vue"
import PipeTitle from "@/components/graylog/Pipelines/PipeTitle.vue"

const props = defineProps<{
	minHeight?: string
}>()
const { minHeight } = toRefs(props)

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
})
</script>
