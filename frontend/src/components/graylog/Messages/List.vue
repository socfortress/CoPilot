<template>
	<n-spin :show="loading">
		<div class="flex items-center justify-end gap-2">
			<div class="flex grow gap-5">
				<n-popover overlap placement="bottom-start">
					<template #trigger>
						<div class="bg-default rounded-lg">
							<n-button size="small" class="cursor-help!">
								<template #icon>
									<Icon :name="InfoIcon" />
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
		<div class="my-3 flex min-h-52 flex-col gap-2">
			<template v-if="messages.length">
				<MessageItem v-for="msg of messages" :key="msg.id" :message="msg" />
			</template>
			<template v-else>
				<n-empty v-if="!loading" description="No items found" class="h-48 justify-center" />
			</template>
		</div>
		<div class="flex justify-end">
			<n-pagination
				v-if="messages.length > 3"
				v-model:page="currentPage"
				:page-size="pageSize"
				:item-count="total"
				:page-slot="6"
			/>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { MessageExtended } from "@/types/graylog/messages.d"
import { NButton, NEmpty, NPagination, NPopover, NSpin, useMessage } from "naive-ui"
import { nanoid } from "nanoid"
import { onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import MessageItem from "./Item.vue"

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
