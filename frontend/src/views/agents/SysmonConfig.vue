<template>
	<div class="page page-wrapped page-without-footer flex flex-col">
		<SegmentedPage
			main-content-class="!p-0 overflow-hidden grow flex h-full"
			:use-main-scroll="false"
			padding="18px"
			enable-resize
			toolbar-height="54px"
		>
			<template #sidebar-header>Customers</template>
			<template #sidebar-content>
				<n-spin :show="loadingList">
					<template v-if="customers.length">
						<div class="flex flex-col gap-4">
							<CardEntity
								v-for="customer of customers"
								:key="customer"
								hoverable
								clickable
								:highlighted="customer === currentConfig?.customer_code"
								@click.stop="loadConfig(customer)"
							>
								<div class="flex items-center justify-between">
									<div>{{ customer }}</div>
									<n-button text @click.stop="gotoCustomer({ code: customer })">
										<template #icon>
											<Icon :size="14" :name="LinkIcon" />
										</template>
									</n-button>
								</div>
							</CardEntity>
						</div>
					</template>
					<template v-else>
						<n-empty v-if="!loadingList" description="No items found" class="h-48 justify-center" />
					</template>
					<n-dropdown
						v-if="hasCustomersAvailable"
						placement="bottom-start"
						trigger="click"
						:options="customersOptions"
						@select="newConfig($event)"
					>
						<n-button secondary class="!mt-4 !w-full" size="large">
							<template #icon>
								<Icon :size="18" :name="NewConfigIcon" />
							</template>
							<span class="ml-2">Add new Configuration</span>
						</n-button>
					</n-dropdown>
				</n-spin>
			</template>
			<template #main-toolbar>
				<div v-if="currentConfig" class="@container flex items-center justify-between">
					<div class="flex items-center gap-3 md:gap-4">
						<n-button
							v-if="xmlEditorCTX"
							size="small"
							:disabled="!xmlEditorCTX.canUndo()"
							@click="xmlEditorCTX.undo"
						>
							<div class="flex items-center gap-2">
								<Icon :name="UndoIcon" />
								<span class="@sm:flex hidden">Undo</span>
							</div>
						</n-button>
						<n-button
							v-if="xmlEditorCTX"
							size="small"
							:disabled="!xmlEditorCTX.canRedo()"
							@click="xmlEditorCTX.redo"
						>
							<div class="flex items-center gap-2">
								<span class="@sm:flex hidden">Redo</span>
								<Icon :name="RedoIcon" />
							</div>
						</n-button>
					</div>
					<div class="flex items-center gap-3 md:gap-4">
						<n-button
							:loading="uploadingConfig"
							size="small"
							type="primary"
							:disabled="!isDirty"
							@click="uploadConfigFile()"
						>
							<div class="flex items-center gap-2">
								<Icon :name="UploadIcon" />
								<span class="@xs:flex hidden">Upload</span>
							</div>
						</n-button>
						<n-button
							:loading="deployingConfig"
							size="small"
							type="success"
							:disabled="!currentConfig.config_content"
							@click="deployConfig()"
						>
							<div class="flex items-center gap-2">
								<Icon :name="DeployIcon" />
								<span class="@xs:flex hidden">Deploy</span>
							</div>
						</n-button>
					</div>
				</div>
			</template>
			<template #main-content>
				<n-spin
					:show="loadingConfig || uploadingConfig || deployingConfig"
					class="flex h-full w-full overflow-hidden"
					content-class="flex h-full grow flex-col justify-center overflow-hidden"
				>
					<template v-if="currentConfig">
						<XMLEditor
							v-model="currentConfig.config_content"
							class="scrollbar-styled text-sm"
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
import type { Customer } from "@/types/customers"
import type { ConfigContent } from "@/types/sysmonConfig.d"
import type { DropdownMixedOption } from "naive-ui/es/dropdown/src/interface"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import SegmentedPage from "@/components/common/SegmentedPage.vue"
import XMLEditor from "@/components/common/XMLEditor.vue"
import { useGoto } from "@/composables/useGoto"
import _clone from "lodash/cloneDeep"
import { NButton, NDropdown, NEmpty, NSpin, useMessage } from "naive-ui"
import { computed, h, onBeforeMount, ref } from "vue"

const message = useMessage()
const { gotoCustomer } = useGoto()
const loadingList = ref(false)
const loadingConfig = ref(false)
const uploadingConfig = ref(false)
const deployingConfig = ref(false)
const customers = ref<string[]>([])
const currentConfig = ref<ConfigContent | null>(null)
const backupConfig = ref<ConfigContent | null>(null)
const xmlEditorCTX = ref<XMLEditorCtx | null>(null)
const UndoIcon = "carbon:undo"
const RedoIcon = "carbon:redo"
const LinkIcon = "carbon:launch"
const DeployIcon = "carbon:deploy"
const UploadIcon = "carbon:cloud-upload"
const NewConfigIcon = "carbon:document-add"

const isDirty = computed(() => currentConfig.value?.config_content !== backupConfig.value?.config_content)

const loadingCustomersList = ref(false)
const customersList = ref<Customer[]>([])
const hasCustomersAvailable = computed<boolean>(
	() => !!customersList.value.filter(o => !customers.value.includes(o.customer_code)).length
)

const customersOptions = computed(() => {
	const options: DropdownMixedOption[] = []

	options.push({
		label: () => h("div", { class: "pl-2" }, `Select a Customer${loadingCustomersList.value ? "..." : ""}`),
		type: "group",
		children: customersList.value
			.filter(o => !customers.value.includes(o.customer_code))
			.map(o => ({
				label: `#${o.customer_code} - ${o.customer_name}`,
				key: o.customer_code
			}))
	})

	return options
})

function getCustomers() {
	loadingCustomersList.value = true

	Api.customers
		.getCustomers()
		.then(res => {
			if (res.data.success) {
				customersList.value = res.data?.customers || []
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingCustomersList.value = false
		})
}

function newConfig(customerCode: string) {
	customers.value.push(customerCode)
	currentConfig.value = {
		customer_code: customerCode,
		config_content: `<Sysmon schemaversion="4.60">
	<EventFiltering>
		<RuleGroup groupRelation="or"></RuleGroup>
	</EventFiltering>
</Sysmon>`
	}
	backupConfig.value = {
		customer_code: customerCode,
		config_content: `<Sysmon schemaversion="4.60">
	<EventFiltering>
		<RuleGroup groupRelation="or"></RuleGroup>
	</EventFiltering>
</Sysmon>`
	}
	uploadConfigFile()
}

function loadConfig(customerCode: string) {
	if (customerCode !== currentConfig.value?.customer_code) {
		getConfigContent(customerCode)
	}
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
				currentConfig.value = _clone(res.data)
				backupConfig.value = _clone(res.data)
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
					currentConfig.value = _clone(currentConfig.value)
					backupConfig.value = _clone(currentConfig.value)
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
	getCustomers()
})
</script>
