<template>
	<n-spin :show="loading" class="rules-list">
		<n-scrollbar ref="scrollContent">
			<div class="list flex min-h-52 flex-col gap-2">
				<Rule v-for="rule of rules" :key="rule.id" :rule="rule" :highlight="highlight === rule.id" embedded />
			</div>
		</n-scrollbar>
	</n-spin>
</template>

<script setup lang="ts">
import type { ScrollbarInst } from "naive-ui"
import type { PipelineRule } from "@/types/graylog/pipelines.d"
import { NScrollbar, NSpin, useMessage } from "naive-ui"
import { nextTick, onBeforeMount, ref, toRefs, watch } from "vue"
import Api from "@/api"
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
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
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

<style lang="scss" scoped>
.rules-list {
	height: 100%;
	max-height: 100%;
	overflow: hidden;
	box-sizing: border-box;

	:deep() {
		.n-spin-content {
			height: 100%;
			box-sizing: border-box;
			display: flex;
			flex-direction: column;
		}
	}

	.list {
		padding: var(--n-body-padding);
		padding-bottom: 50vh;
	}
}
</style>
