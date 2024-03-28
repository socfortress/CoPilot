<template>
	<div class="stack-provisioning-list">
		<n-spin :show="loading">
			<div class="list my-3">
				<template v-if="list.length">
					<StackProvisioningItem v-for="item of list" :key="item.name" :content-pack="item" class="mb-2" />
				</template>
				<template v-else>
					<n-empty description="No items found" class="justify-center h-48" v-if="!loading" />
				</template>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, computed } from "vue"
import { useMessage, NSpin, NEmpty } from "naive-ui"
import Api from "@/api"
import StackProvisioningItem from "./StackProvisioningItem.vue"
import type { AvailableContentPack } from "@/types/stackProvisioning.d"

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

<style lang="scss" scoped>
.list {
	container-type: inline-size;
	min-height: 200px;
}
</style>
