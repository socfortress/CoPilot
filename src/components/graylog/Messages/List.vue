<template>
	<n-spin :show="loading">
		<div class="header flex justify-end gap-2">
			<n-pagination v-model:page="currentPage" :page-size="pageSize" :item-count="total" :page-slot="6" />
		</div>
		<div class="list my-3">
			<MessageItem v-for="msg of messages" :key="msg.id" :message="msg" />
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
import { useMessage, NSpin, NPagination } from "naive-ui"
import Api from "@/api"
import MessageItem, { type MessageExt } from "./Item.vue"
import { nanoid } from "nanoid"
import dayjs from "dayjs"
import { useSettingsStore } from "@/stores/settings"

const dFormats = useSettingsStore().dateFormat
const message = useMessage()
const loading = ref(false)
const messages = ref<MessageExt[]>([])
const total = ref(0)
const pageSize = ref(1)
const currentPage = ref(1)

function getData(page: number) {
	loading.value = true

	Api.graylog
		.getMessages(page)
		.then(res => {
			if (res.data.success) {
				const data = (res.data.graylog_messages || []) as MessageExt[]
				messages.value = data.map(o => {
					o.id = nanoid()
					o.timestamp = dayjs(o.timestamp).format(dFormats.datetimesec)
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
}
</style>
