<template>
	<n-spin :show="loading" class="box-border h-full max-h-full overflow-hidden" content-class="flex h-full flex-col">
		<n-scrollbar ref="scrollContent">
			<div class="flex min-h-52 flex-col gap-2 p-(--n-body-padding) pb-[50vh]">
				<Rule v-for="rule of rules" :key="rule.id" :rule :highlight="highlight === rule.id" embedded />
			</div>
		</n-scrollbar>
	</n-spin>
</template>

<script setup lang="ts">
import type { ScrollbarInst } from "naive-ui"
import type { ApiError } from "@/types/common"
import type { PipelineRule } from "@/types/graylog/pipelines"
import { NScrollbar, NSpin, useMessage } from "naive-ui"
import { nextTick, onBeforeMount, ref, toRefs, watch } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"
import Rule from "./Rule.vue"

const props = defineProps<{ highlight: string | null | undefined }>()

const emit = defineEmits<{
	(e: "loaded", value: { total: number }): void
}>()

const { highlight } = toRefs(props)

const message = useMessage()
const loading = ref(false)
const rules = ref<PipelineRule[]>([])
const scrollContent = ref<(ScrollbarInst & { $el: HTMLElement }) | null>(null)

function scrollToItem(id: string) {
	const element = document.getElementById(`rule-${id}`)
	if (element && scrollContent.value) {
		const wrap = (scrollContent.value.$el.nextSibling || scrollContent.value.$el.nextElementSibling) as HTMLElement
		const middle = element.offsetTop - wrap.offsetHeight / 2
		scrollContent.value?.scrollTo({ top: middle, behavior: "smooth" })
	}
}

function getRules() {
	loading.value = true

	Api.graylog
		.getPipelinesRules()
		.then(res => {
			if (res.data.success) {
				rules.value = res.data.pipeline_rules || []
				emit("loaded", { total: rules.value.length })
				nextTick(() => {
					setTimeout(() => {
						if (highlight.value) {
							scrollToItem(highlight.value)
						}
					}, 300)
				})
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

watch(highlight, val => {
	if (val) {
		nextTick(() => {
			setTimeout(() => {
				scrollToItem(val)
			})
		})
	}
})

onBeforeMount(() => {
	getRules()
})
</script>
