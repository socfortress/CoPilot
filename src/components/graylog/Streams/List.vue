<template>
	<n-spin :show="loading">
		<div class="header flex items-center justify-end gap-2" ref="header">
			<div class="info grow flex gap-5">
				<n-popover overlap placement="bottom-start">
					<template #trigger>
						<div class="bg-color border-radius">
							<n-button size="small">
								<template #icon>
									<Icon :name="InfoIcon"></Icon>
								</template>
							</n-button>
						</div>
					</template>
					<div class="flex flex-col gap-2">
						<div class="box">
							Total:
							<code>{{ total }}</code>
						</div>
					</div>
				</n-popover>
			</div>
			<n-pagination
				v-model:page="currentPage"
				v-model:page-size="pageSize"
				:page-slot="pageSlot"
				:show-size-picker="showSizePicker"
				:page-sizes="pageSizes"
				:item-count="total"
				:simple="simpleMode"
			/>
		</div>
		<div class="list my-3">
			<StreamItem v-for="stream of itemsPaginated" :key="stream.id" :stream="stream" />
		</div>
		<div class="footer flex justify-end">
			<n-pagination
				v-model:page="currentPage"
				:page-size="pageSize"
				:item-count="total"
				:page-slot="6"
				v-if="itemsPaginated.length > 3"
			/>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, computed } from "vue"
import { useMessage, NSpin, NPagination, NPopover, NButton } from "naive-ui"
import Api from "@/api"
import StreamItem from "./Item.vue"
import Icon from "@/components/common/Icon.vue"
import type { Stream } from "@/types/graylog/stream.d"
import { useResizeObserver } from "@vueuse/core"

const InfoIcon = "carbon:information"

const message = useMessage()
const loading = ref(false)
const streams = ref<Stream[]>([])
const total = ref(0)
const pageSize = ref(25)
const currentPage = ref(1)
const simpleMode = ref(false)
const showSizePicker = ref(true)
const pageSizes = [10, 25, 50, 100]
const header = ref()
const pageSlot = ref(8)

const itemsPaginated = computed(() => {
	const from = (currentPage.value - 1) * pageSize.value
	const to = currentPage.value * pageSize.value
	return streams.value.slice(from, to)
})

function getData() {
	loading.value = true

	Api.graylog
		.getStreams()
		.then(res => {
			if (res.data.success) {
				streams.value = res.data.streams || []
				total.value = res.data.total || 0
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

useResizeObserver(header, entries => {
	const entry = entries[0]
	const { width } = entry.contentRect

	pageSlot.value = width < 650 ? 5 : 8
	simpleMode.value = width < 450
})

onBeforeMount(() => {
	getData()
})
</script>

<style lang="scss" scoped>
.list {
	container-type: inline-size;
}
</style>
