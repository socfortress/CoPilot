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

		<PipeList @open-rule="openRule($event)" minHeight="100px" />

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
					<span class="font-mono ml-2 text-secondary-color" v-if="rulesTotal !== null">{{ rulesTotal }}</span>
				</template>
				<RulesList @loaded="rulesTotal = $event.total" :highlight="highlightRule" />
			</n-drawer-content>
		</n-drawer>
	</div>
</template>

<script setup lang="ts">
import { NButton, NModal, NDrawer, NDrawerContent } from "naive-ui"
import { onBeforeMount, ref, watch } from "vue"
import type { PipelineFull } from "@/types/graylog/pipelines.d"
import Icon from "@/components/common/Icon.vue"
import PipeList from "@/components/graylog/Pipelines/PipeList.vue"
import PipeInfo from "@/components/graylog/Pipelines/PipeInfo.vue"
import RulesList from "@/components/graylog/Pipelines/RulesList.vue"
import { useRoute } from "vue-router"

const RulesIcon = "ic:outline-swipe-right-alt"

const route = useRoute()
const showDetails = ref(false)
const highlightPipe = ref<PipelineFull | undefined>(undefined)
const highlightRule = ref<string | null>(null)
const showRulesDrawer = ref(false)
const rulesTotal = ref<null | number>(null)

function openRule(id: string) {
	highlightRule.value = id
	showRulesDrawer.value = true
}

watch(showRulesDrawer, val => {
	if (!val) {
		highlightRule.value = null
	}
})

onBeforeMount(() => {
	if (route.query?.rule) {
		openRule(route.query.rule.toString())
	}
})
</script>
