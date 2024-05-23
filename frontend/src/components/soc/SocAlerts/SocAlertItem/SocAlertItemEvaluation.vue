<template>
	<code class="cursor-pointer text-primary-color" @click="openEvaluation()">
		{{ processName }}
		<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
	</code>

	<n-modal
		v-model:show="showDetails"
		preset="card"
		content-class="!p-0"
		:style="{ maxWidth: 'min(800px, 90vw)', minHeight: 'min(550px, 90vh)', overflow: 'hidden' }"
		:title="`Evaluation: ${processName}`"
		:bordered="false"
		segmented
	>
		<div>
			<pre>{{ evaluation }}</pre>
		</div>
	</n-modal>
</template>

<script setup lang="ts">
import Icon from "@/components/common/Icon.vue"
import KVCard from "@/components/common/KVCard.vue"
import { NCollapse, useMessage, NCollapseItem, NModal, NSpin, NCheckbox, NCollapseTransition } from "naive-ui"
import type { EvaluationData } from "@/types/threatIntel"
import { ref } from "vue"
import Api from "@/api"

const { processName } = defineProps<{
	processName: string
}>()

const LinkIcon = "carbon:launch"
const evaluation = ref<EvaluationData | null>(null)
const showDetails = ref<boolean>(false)
const loading = ref<boolean>(false)
const message = useMessage()

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
