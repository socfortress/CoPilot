<template>
	<div class="page page-wrapped page-mobile-full page-without-footer flex flex-col">
		<SegmentedPage
			main-content-class="p-0! overflow-hidden grow flex flex-col h-full"
			:use-main-scroll="false"
			padding="18px"
			enable-resize
			toolbar-height="54px"
			sidebar-content-class="p-0!"
		>
			<template #sidebar-header>Customers</template>
			<template #sidebar-content>
				<n-spin :show="loadingList">
					<template v-if="customers.length">
						<div class="divide-border flex flex-col divide-y">
							<div
								v-for="customer of customers"
								:key="customer"
								class="hover:text-warning flex cursor-pointer items-center justify-between px-4.5 py-2.5 text-sm break-all"
								:class="{ 'bg-warning/10': customer === currentConfig?.customer_code }"
								@click.stop="loadConfig(customer)"
							>
								<div class="font-mono">{{ customer }}</div>
								<n-tooltip class="px-2! py-1.5! text-xs!">
									<template #trigger>
										<n-button
											size="tiny"
											secondary
											@click.stop="routeCustomer({ code: customer }).navigate()"
										>
											<template #icon>
												<Icon :name="LinkIcon" />
											</template>
										</n-button>
									</template>
									Go to Customer
								</n-tooltip>
							</div>
						</div>
					</template>
					<template v-else>
						<n-empty v-if="!loadingList" description="No items found" class="h-48 justify-center" />
					</template>
					<div class="p-4">
						<n-dropdown
							v-if="hasCustomersAvailable"
							placement="bottom-start"
							trigger="click"
							:options="customersOptions"
							@select="newConfig($event)"
						>
							<n-button secondary class="mt-4! w-full!" size="large">
								<template #icon>
									<Icon :size="18" :name="NewConfigIcon" />
								</template>
								<span class="ml-1.5 truncate">Add new Configuration</span>
							</n-button>
						</n-dropdown>
					</div>
				</n-spin>
			</template>
			<template #main-toolbar>
				<div v-if="currentConfig" class="@container flex items-center justify-between">
					<div class="flex items-center gap-2 md:gap-3">
						<n-button
							v-if="xmlEditorRef"
							size="small"
							:disabled="!xmlEditorRef.canUndo()"
							@click="xmlEditorRef.undo"
						>
							<div class="flex items-center gap-2">
								<Icon :name="UndoIcon" />
								<span class="hidden @sm:flex">Undo</span>
							</div>
						</n-button>
						<n-button
							v-if="xmlEditorRef"
							size="small"
							:disabled="!xmlEditorRef.canRedo()"
							@click="xmlEditorRef.redo"
						>
							<div class="flex items-center gap-2">
								<span class="hidden @sm:flex">Redo</span>
								<Icon :name="RedoIcon" />
							</div>
						</n-button>
					</div>
					<div class="flex items-center gap-2 md:gap-3">
						<n-popover v-if="xmlErrors.length && xmlEditorRef" class="p-1!">
							<template #trigger>
								<div class="flex items-center justify-end gap-2">
									<Icon
										name="carbon:warning-alt"
										:size="20"
										class="text-warning animate-fade cursor-help"
									/>
									<span class="text-warning hidden font-mono text-xs @lg:flex">Errors detected</span>
								</div>
							</template>

							<n-scrollbar class="max-h-100">
								<div class="flex max-w-80 flex-col gap-1">
									<div
										v-for="item of xmlErrors"
										:key="JSON.stringify(item)"
										class="bg-secondary hover:bg-body flex cursor-pointer flex-col gap-0.5 rounded-sm p-1 font-mono"
										@click="xmlEditorRef.scrollToLine(item.line)"
									>
										<div class="text-secondary text-[8px]">line: {{ item.line }}</div>
										<div class="text-xs">{{ item.message }}</div>
									</div>
								</div>
							</n-scrollbar>
						</n-popover>

						<n-button
							:loading="uploadingConfig"
							size="small"
							type="primary"
							:disabled="!isDirty"
							@click="uploadConfigFile()"
						>
							<div class="flex items-center gap-2">
								<Icon :name="UploadIcon" />
								<span class="hidden @xs:flex">Upload</span>
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
								<span class="hidden @xs:flex">Deploy</span>
							</div>
						</n-button>
					</div>
				</div>
			</template>
			<template #main-content>
				<div v-if="currentConfig" class="px-4.5 py-2.5 text-sm break-all">
					<div class="font-mono">Customer: {{ currentConfig?.customer_code }}</div>
				</div>
				<n-spin
					:show="loadingConfig || uploadingConfig || deployingConfig"
					class="flex h-full w-full overflow-hidden"
					content-class="flex h-full grow flex-col justify-center overflow-hidden"
				>
					<template v-if="currentConfig">
						<XMLEditor
							ref="xmlEditorRef"
							v-model="currentConfig.config_content"
							class="scrollbar-styled text-sm"
							@errors="xmlErrors = $event"
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
import type { DropdownMixedOption } from "naive-ui/es/dropdown/src/interface"
import type { XMLEditorCtx, XMLError } from "@/components/common/XMLEditor.vue"
import type { ApiError } from "@/types/common"
import type { Customer } from "@/types/customers"
import type { ConfigContent } from "@/types/sysmonConfig.d"
import _clone from "lodash/cloneDeep"
import { NButton, NDropdown, NEmpty, NPopover, NScrollbar, NSpin, NTooltip, useMessage } from "naive-ui"
import { computed, h, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import SegmentedPage from "@/components/common/SegmentedPage.vue"
import XMLEditor from "@/components/common/XMLEditor.vue"
import { useNavigation } from "@/composables/useNavigation"
import { getApiErrorMessage } from "@/utils"

const message = useMessage()
const { routeCustomer } = useNavigation()
const loadingList = ref(false)
const loadingConfig = ref(false)
const uploadingConfig = ref(false)
const deployingConfig = ref(false)
const customers = ref<string[]>([])
const currentConfig = ref<ConfigContent | null>(null)
const backupConfig = ref<ConfigContent | null>(null)
const xmlEditorRef = ref<XMLEditorCtx | null>(null)
const UndoIcon = "carbon:undo"
const RedoIcon = "carbon:redo"
const LinkIcon = "carbon:launch"
const DeployIcon = "carbon:deploy"
const UploadIcon = "carbon:cloud-upload"
const NewConfigIcon = "carbon:document-add"

const isDirty = computed(() => currentConfig.value?.config_content !== backupConfig.value?.config_content)
const xmlErrors = ref<XMLError[]>([])

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
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
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
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
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
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
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
				message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
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
				message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
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
