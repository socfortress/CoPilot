<template>
	<n-spin :show="loading">
		<div class="header flex items-center justify-end gap-2">
			<div class="info grow flex gap-5">
				<n-popover overlap placement="bottom-start">
					<template #trigger>
						<div class="bg-color border-radius">
							<n-button size="small" class="!cursor-help">
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
			<n-pagination v-model:page="currentPage" :page-size="pageSize" :item-count="total" :page-slot="5" />
		</div>
		<div class="list my-3">
			<template v-if="messages.length">
				<MessageItem v-for="msg of messages" :key="msg.id" :message="msg" class="mb-2" />
			</template>
			<template v-else>
				<n-empty description="No items found" class="justify-center h-48" v-if="!loading" />
			</template>
		</div>
		<div class="footer flex justify-end">
			<n-pagination
				v-model:page="currentPage"
				:page-size="pageSize"
				:item-count="total"
				:page-slot="6"
				v-if="messages.length > 3"
			/>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, watch } from "vue"
import { useMessage, NSpin, NPagination, NPopover, NButton, NEmpty } from "naive-ui"
import Api from "@/api"
import MessageItem from "./Item.vue"
import Icon from "@/components/common/Icon.vue"
import { nanoid } from "nanoid"
import type { MessageExtended } from "@/types/graylog/index.d"

const InfoIcon = "carbon:information"

const message = useMessage()
const loading = ref(false)
const messages = ref<MessageExtended[]>([])
const total = ref(0)
const pageSize = ref(1)
const currentPage = ref(1)

function getData(page: number) {
	loading.value = true

	Api.graylog
		.getMessages(page)
		.then(res => {
			if (res.data.success) {
				const data = (res.data.graylog_messages || []) as MessageExtended[]
				messages.value = data.map(o => {
					o.id = nanoid()
					return o
				})
				total.value = res.data.total_messages || 0
				if (pageSize.value <= 1) pageSize.value = messages.value.length
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

watch(currentPage, val => {
	getData(val)
})

onBeforeMount(() => {
	getData(currentPage.value)
})
</script>

<style lang="scss" scoped>
.list {
	container-type: inline-size;
	min-height: 200px;
}
</style>
