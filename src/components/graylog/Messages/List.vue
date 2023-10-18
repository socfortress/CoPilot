<template>
	<n-spin :show="loading">
		<div class="header flex justify-end" ref="paginationContainer">
			<n-pagination
				v-model:page="currentPage"
				:page-size="pageSize"
				:item-count="total"
				:page-slot="6"
				v-if="total"
			/>
		</div>
		<div class="list my-3">
			<MessageItem v-for="msg of messages" :key="msg.id" :message="msg" />
		</div>
		<div class="footer flex justify-end" ref="paginationContainer">
			<n-pagination
				v-model:page="currentPage"
				:page-size="pageSize"
				:item-count="total"
				:page-slot="6"
				v-if="total"
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
const paginationContainer = ref(null)
const loading = ref(false)
const messages = ref<MessageExt[]>([])
const total = ref(0)
const pageSize = ref(0)
const currentPage = ref(1)

function getMessages(page: number) {
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
				if (!pageSize.value) pageSize.value = messages.value.length
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
	getMessages(val)
})

onBeforeMount(() => {
	getMessages(currentPage.value)
})
</script>

<style lang="scss" scoped>
.list {
	container-type: inline-size;
}
</style>
