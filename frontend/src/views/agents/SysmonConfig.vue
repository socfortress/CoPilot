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
				<n-spin :show="loadingList" class="min-h-48">
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
							v-if="isAdmin && hasCustomersAvailable"
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

						<!-- Saves the editor's text as this CoPilot's default, which pre-fills "Add new Configuration". The
							customer's stored config, and whether the editor has unsaved changes, stay as they are. -->
						<n-button
							v-if="isAdmin && currentConfig.config_content"
							:loading="savingDefault"
							size="small"
							type="info"
							@click="confirmSaveAsDefault()"
						>
							<div class="flex items-center gap-2">
								<Icon :name="SaveDefaultIcon" />
								<span class="hidden @xs:flex">Save as default</span>
							</div>
						</n-button>
						<n-button
							v-if="isAdmin"
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
						<!-- Deploy ships the stored copy, not the editor's text: unsaved changes must be uploaded first. -->
						<n-button
							:loading="deployingConfig"
							size="small"
							type="success"
							:disabled="!currentConfig.config_content || isDirty"
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
					content-class="flex h-full grow flex-col overflow-hidden"
				>
					<template v-if="currentConfig">
						<!-- A responder deploys their customers' configs; writing one stays admin (#1219). -->
						<XMLEditor
							ref="xmlEditorRef"
							v-model="currentConfig.config_content"
							:readonly="!isAdmin"
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
import type { MessageReactive } from "naive-ui"
import type { DropdownMixedOption } from "naive-ui/es/dropdown/src/interface"
import type { XMLEditorCtx, XMLError } from "@/components/common/XMLEditor.vue"
import type { ApiError } from "@/types/common"
import type { Customer } from "@/types/customers"
import type { ConfigContent } from "@/types/sysmon-config"
import _clone from "lodash/cloneDeep"
import { NButton, NDropdown, NEmpty, NPopover, NScrollbar, NSpin, NTooltip, useDialog, useMessage } from "naive-ui"
import { computed, h, onBeforeMount, onBeforeUnmount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import SegmentedPage from "@/components/common/SegmentedPage.vue"
import XMLEditor from "@/components/common/XMLEditor.vue"
import { useNavigation } from "@/composables/useNavigation"
import { useAuthStore } from "@/stores/auth"
import { getApiErrorMessage } from "@/utils"

const message = useMessage()
const dialog = useDialog()
const { routeCustomer } = useNavigation()
const isAdmin = computed(() => useAuthStore().isAdmin)
const loadingList = ref(false)
const loadingConfig = ref(false)
const uploadingConfig = ref(false)
const deployingConfig = ref(false)
const savingDefault = ref(false)
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
const SaveDefaultIcon = "carbon:template"

const isDirty = computed(() => currentConfig.value?.config_content !== backupConfig.value?.config_content)
const xmlErrors = ref<XMLError[]>([])

const loadingCustomersList = ref(false)
const customersList = ref<Customer[]>([])
const hasCustomersAvailable = computed<boolean>(() =>
	customersList.value.some(o => !customers.value.includes(o.customer_code))
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
		.getCustomers({})
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

const EMPTY_CONFIG = `<Sysmon schemaversion="4.60">
	<EventFiltering>
		<RuleGroup groupRelation="or"></RuleGroup>
	</EventFiltering>
</Sysmon>`

// Which customer the editor is being opened for: a response for an earlier pick (another customer was chosen while it
// was in flight) is dropped.
let editorRequest = 0
let defaultConfigController: AbortController | null = null
let prefillNotice: MessageReactive | null = null

function startEditorRequest() {
	defaultConfigController?.abort()
	defaultConfigController = null
	prefillNotice?.destroy()
	prefillNotice = null
	return ++editorRequest
}

// A new configuration opens as unsaved content (Upload enabled, Deploy disabled): this CoPilot's default Sysmon config
// rendered for the customer when one is set, else an empty skeleton. Nothing is stored until an admin uploads a real
// config (the backend refuses one without event filters).
function newConfig(customerCode: string) {
	const request = startEditorRequest()
	const controller = new AbortController()
	defaultConfigController = controller
	currentConfig.value = null
	backupConfig.value = null
	loadingConfig.value = true

	const open = (content: string) => {
		currentConfig.value = { customer_code: customerCode, config_content: content }
		backupConfig.value = null
	}

	Api.sysmonConfig
		.getDefaultConfig(customerCode, controller.signal)
		.then(res => {
			if (request !== editorRequest) return

			if (res.data.success && res.data.present && res.data.config_content) {
				open(res.data.config_content.replace(/\r\n?/g, "\n"))
				const code = res.data.rendered_for || customerCode
				prefillNotice = message.info(
					`Pre-filled from this CoPilot's default Sysmon config. Install-folder paths use "${code}": change them if this customer's installer uses a different install folder. Nothing is stored until you upload.`,
					{ duration: 0, closable: true }
				)
			} else {
				open(EMPTY_CONFIG)
				message.info(
					`No default Sysmon config is set on this CoPilot, so the editor starts from an empty skeleton. An admin can set one with "Save as default".`,
					{ duration: 10000, closable: true }
				)
			}
		})
		.catch(err => {
			if (request !== editorRequest) return

			open(EMPTY_CONFIG)
			message.warning(
				`This CoPilot's default Sysmon config could not be loaded: ${getApiErrorMessage(err as ApiError)} The editor starts from an empty skeleton. An admin can set a default with "Save as default".`,
				{ duration: 10000, closable: true }
			)
		})
		.finally(() => {
			if (request === editorRequest) {
				loadingConfig.value = false
				defaultConfigController = null
			}
		})
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
	const request = startEditorRequest()
	loadingConfig.value = true

	Api.sysmonConfig
		.getConfigContent(customerCode)
		.then(res => {
			if (request !== editorRequest) return

			if (res.data.success) {
				// The editor keeps "\n" line breaks only, and hands a CRLF file back as changed as soon as it takes
				// it. That would mark the stored config unsaved and keep Deploy disabled, so both copies start
				// from the editor's line breaks.
				const config = { ...res.data, config_content: res.data.config_content?.replace(/\r\n?/g, "\n") }
				currentConfig.value = _clone(config)
				backupConfig.value = _clone(config)
			} else {
				message.error(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			if (request !== editorRequest) return

			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			if (request === editorRequest) {
				loadingConfig.value = false
			}
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
					if (!customers.value.includes(res.data.customer_code)) {
						customers.value.push(res.data.customer_code)
					}
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
					message.success(res.data.message || "Sysmon Config deployed successfully")
					// The endpoints only apply the config through the group's sysmon-reload wodle.
					if (res.data.sysmon_health_warning) {
						message.warning(res.data.sysmon_health_warning, { duration: 0, closable: true })
					}
				} else {
					message.error(res.data?.message || "An error occurred. Please try again later.")
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

// What the dialog names is what gets saved, whatever the editor holds by the time it is confirmed.
function confirmSaveAsDefault() {
	if (!currentConfig.value?.config_content) return

	const { customer_code: customerCode, config_content: configContent } = currentConfig.value

	dialog.warning({
		title: "Save as default",
		// Plain text, never HTML: the customer code is data.
		content: `Replace this CoPilot's default Sysmon config? "Add new Configuration" pre-fills new customers with it. Install-folder paths for "${customerCode}" are turned back into the __INSTALLDIRNAME__ placeholder.`,
		positiveText: "Save as default",
		negativeText: "Cancel",
		onPositiveClick: () => {
			saveAsDefault(configContent, customerCode)
		}
	})
}

// Leaves the customer's stored config and the editor (including its unsaved state) as they are.
function saveAsDefault(configContent: string, customerCode: string) {
	savingDefault.value = true

	Api.sysmonConfig
		.saveDefaultConfig(configContent, customerCode)
		.then(res => {
			if (res.data.success) {
				// Without a placeholder, every new configuration gets these exact install-folder paths.
				if (res.data.placeholders === 0) {
					message.warning(res.data.message, { duration: 0, closable: true })
				} else {
					message.success(res.data.message || "Saved as this CoPilot's default Sysmon config", {
						duration: 10000,
						closable: true
					})
				}
			} else {
				message.error(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			savingDefault.value = false
		})
}

onBeforeMount(() => {
	getList()
	getCustomers()
})

onBeforeUnmount(() => {
	// Drops a default still loading, so its message never shows up on another page.
	startEditorRequest()
})
</script>
