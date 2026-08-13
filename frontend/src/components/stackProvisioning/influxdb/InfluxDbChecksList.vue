<template>
	<div class="influxdb-checks-list">
		<n-spin :show="loading">
			<div class="my-3 flex min-h-52 flex-col gap-2">
				<template v-if="list.length">
					<div class="flex justify-end">
						<n-button :loading="loadingProvisionAll" type="success" size="small" @click="provisionAll()">
							<template #icon>
								<Icon :name="DeployIcon" />
							</template>
							Deploy all missing
						</n-button>
					</div>
					<InfluxDbCheckItem v-for="item of list" :key="item.name" :check="item" @provisioned="getData()" />
				</template>
				<template v-else>
					<n-empty v-if="!loading" description="No items found" class="h-48 justify-center" />
				</template>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { AvailableInfluxDbCheck } from "@/types/stack-provisioning"
import { NButton, NEmpty, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"
import InfluxDbCheckItem from "./InfluxDbCheckItem.vue"

const DeployIcon = "mdi:package-variant-closed-check"
const message = useMessage()
const loadingList = ref(false)
const loadingProvisionAll = ref(false)
const list = ref<AvailableInfluxDbCheck[]>([])
const loading = computed(() => loadingList.value || loadingProvisionAll.value)

function getData() {
	loadingList.value = true

	Api.stackProvisioning
		.getAvailableInfluxDbChecks()
		.then(res => {
			if (res.data.success) {
				list.value = res.data.available_checks || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingList.value = false
		})
}

function provisionAll() {
	loadingProvisionAll.value = true

	// overwrite stays false here: bulk deploy fills in what is missing and leaves existing
	// checks alone. Replacing one is a deliberate per-check action.
	Api.stackProvisioning
		.provisionInfluxDbChecks(false)
		.then(res => {
			if (res.data.success) {
				message.success(res.data?.message || "InfluxDB Checks Provisioned Successfully")
				getData()
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingProvisionAll.value = false
		})
}

onBeforeMount(() => {
	getData()
})
</script>
