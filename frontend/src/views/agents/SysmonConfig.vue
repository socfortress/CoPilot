<template>
	<div class="page page-wrapped page-without-footer flex flex-col">
		<SegmentedPage main-content-class="!p-0 overflow-hidden grow flex h-full" :use-main-scroll="false">
			<template #sidebar-header>Customers</template>
			<template #sidebar-content>
				<n-spin :show="loadingList">
					<template v-if="customers.length">
						<div class="flex flex-col gap-4">
							<div v-for="customer of customers" :key="customer" @click.stop="loadConfig(customer)">
								<div>{{ customer }}</div>
								<button @click.stop="gotoCustomer({ code: customer })">open</button>
							</div>
						</div>
					</template>
					<template v-else>
						<n-empty v-if="!loadingList" description="No items found" class="h-48 justify-center" />
					</template>
				</n-spin>
			</template>
			<template #main-toolbar>
				<div class="flex items-center justify-between">
					<div class="flex items-center gap-4">
						<n-button v-if="xmlEditorCTX" @click="xmlEditorCTX.undo">undo</n-button>
						<n-button v-if="xmlEditorCTX" @click="xmlEditorCTX.redo">redo</n-button>
					</div>
					<div v-if="currentConfig" class="flex items-center gap-4">
						<n-button :loading="uploadingConfig" @click="uploadConfigFile()">Upload</n-button>
						<n-button :loading="deployingConfig" @click="deployConfig()">Deploy</n-button>
					</div>
				</div>
			</template>
			<template #main-content>
				<n-spin
					:show="loadingConfig || uploadingConfig || deployingConfig"
					class="flex h-full overflow-hidden"
					content-class="overflow-hidden grow h-full"
				>
					<template v-if="currentConfig">
						<XMLEditor
							v-model="currentConfig.config_content"
							class="text-sm"
							@mounted="xmlEditorCTX = $event"
						/>
					</template>
					<template v-else>
						<n-empty v-if="!loadingConfig" description="Select a customer" class="h-48 justify-center" />
					</template>
				</n-spin>
			</template>
		</SegmentedPage>
	</div>
</template>

<script setup lang="ts">
import type { XMLEditorCtx } from "@/components/common/XMLEditor.vue"
import type { ConfigContent } from "@/types/sysmonConfig.d"
import Api from "@/api"
import SegmentedPage from "@/components/common/SegmentedPage.vue"
import XMLEditor from "@/components/common/XMLEditor.vue"
import { useGoto } from "@/composables/useGoto"
import { NButton, NEmpty, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"

const message = useMessage()
const { gotoCustomer } = useGoto()
const loadingList = ref(false)
const loadingConfig = ref(false)
const uploadingConfig = ref(false)
const deployingConfig = ref(false)
const customers = ref<string[]>([])
const currentConfig = ref<ConfigContent | null>(null)
const xmlEditorCTX = ref<XMLEditorCtx | null>(null)

function loadConfig(customerCode: string) {
	getConfigContent(customerCode)
}

function getList() {
	loadingList.value = true

	Api.sysmonConfig
		.getAll()
		.then(res => {
			if (res.data.success) {
				customers.value = res.data.customer_codes || []
			} else {
				message.error(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingList.value = false
		})
}

function getConfigContent(customerCode: string) {
	loadingConfig.value = true

	Api.sysmonConfig
		.getConfigContent(customerCode)
		.then(res => {
			if (res.data.success) {
				currentConfig.value = res.data
			} else {
				message.error(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingConfig.value = false
		})
}

function uploadConfigFile() {
	if (currentConfig.value) {
		uploadingConfig.value = true

		Api.sysmonConfig
			.uploadConfigFile(
				currentConfig.value.customer_code,
				new File(
					[currentConfig.value.config_content],
					`sysmon_config-${currentConfig.value.customer_code}.xml`,
					{ type: "text/xml;charset=utf-8" }
				)
			)
			.then(res => {
				if (res.data.success) {
					message.success("Sysmon Config uploaded Successfully")
				} else {
					message.error("An error occurred. Please try again later.")
				}
			})
			.catch(err => {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			})
			.finally(() => {
				uploadingConfig.value = false
			})
	}
}

function deployConfig() {
	if (currentConfig.value) {
		deployingConfig.value = true

		Api.sysmonConfig
			.deployConfig(currentConfig.value.customer_code)
			.then(res => {
				if (res.data.success) {
					message.success("Sysmon Config deployed successfully")
				} else {
					message.error("An error occurred. Please try again later.")
				}
			})
			.catch(err => {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			})
			.finally(() => {
				deployingConfig.value = false
			})
	}
}

onBeforeMount(() => {
	getList()
})
</script>
