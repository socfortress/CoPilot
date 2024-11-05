<template>
	<div class="stack-provisioning-list">
		<n-spin :show="loading">
			<div class="my-3 flex min-h-52 flex-col gap-2">
				<template v-if="list.length">
					<StackProvisioningItem v-for="item of list" :key="item.name" :content-pack="item" />
				</template>
				<template v-else>
					<n-empty v-if="!loading" description="No items found" class="h-48 justify-center" />
				</template>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { AvailableContentPack } from "@/types/stackProvisioning.d"
import Api from "@/api"
import { NEmpty, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import StackProvisioningItem from "./StackProvisioningItem.vue"

const message = useMessage()
const loadingList = ref(false)
const list = ref<AvailableContentPack[]>([])
const loading = computed(() => loadingList.value)

function getData() {
	loadingList.value = true

	Api.stackProvisioning
		.getAvailableContentPacks()
		.then(res => {
			if (res.data.success) {
				list.value = res.data.available_content_packs || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingList.value = false
		})
}

onBeforeMount(() => {
	getData()
})
</script>
