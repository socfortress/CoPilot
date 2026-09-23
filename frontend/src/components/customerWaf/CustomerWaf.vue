<template>
	<div class="flex flex-col gap-4">
		<div class="flex flex-wrap items-start justify-between gap-3">
			<div class="flex flex-col gap-1">
				<h3 class="text-lg font-bold">WAF</h3>
				<p class="text-secondary text-sm">
					SOCFortress WAFs protecting this customer's applications. Set them up here; view their events,
					threat intel and blocks under
					<b>Investigate → WAF</b>
					.
				</p>
			</div>
			<n-button v-if="isAdmin" type="primary" :disabled="!keyConfigured" @click="openForm(null)">
				<template #icon>
					<Icon :name="AddIcon" />
				</template>
				Add WAF
			</n-button>
		</div>

		<n-alert v-if="!keyConfigured && !loading" type="warning" :bordered="false">
			WAFs can't be saved until
			<code>WAF_TOKEN_ENCRYPTION_KEY</code>
			is set in CoPilot's
			<code>.env</code>
			(it encrypts the WAF tokens). Generate one with
			<code>python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"</code>
			and restart the backend.
		</n-alert>
		<n-alert v-if="!isAdmin" type="info" :bordered="false" class="text-xs">
			Only administrators can add or change WAFs.
		</n-alert>
		<CustomerWafError v-if="error" :error />

		<n-spin :show="loading">
			<n-empty
				v-if="!instances.length && !loading"
				description="No WAF configured for this customer"
				class="h-32 justify-center"
			/>
			<div class="flex flex-col gap-3">
				<n-card
					v-for="waf of instances"
					:key="waf.id"
					size="small"
				>
					<div class="flex flex-wrap items-center justify-between gap-3">
						<div class="flex min-w-0 flex-col gap-1">
							<div class="flex flex-wrap items-center gap-2">
								<span class="font-semibold">{{ waf.name }}</span>
								<n-tag size="small" :type="wafCapabilityLabel(waf).type" :bordered="false">
									{{ wafCapabilityLabel(waf).label }}
								</n-tag>
								<n-tag v-if="!waf.enabled" size="small" :bordered="false">Disabled</n-tag>
							</div>
							<div class="text-secondary font-mono text-xs break-all">{{ waf.api_url }}</div>
							<div class="text-secondary text-xs">
								Token
								<span class="font-mono">{{ waf.token_prefix }}</span>
								<template v-if="waf.last_verified_at">
									· verified {{ formatDate(waf.last_verified_at, dFormats.datetime) }} as
									<span class="font-mono">{{ waf.last_verified_role }}</span>
								</template>
							</div>
						</div>
						<div class="flex flex-wrap gap-2">
							<n-button size="small" :loading="verifying === waf.id" @click="verify(waf)">
								Test connection
							</n-button>
							<n-button
								size="small"
								secondary
								type="primary"
								:disabled="!waf.enabled"
								@click="openWafPage(waf)"
							>
								<template #icon>
									<Icon :name="OpenIcon" />
								</template>
								Open in WAF page
							</n-button>
							<template v-if="isAdmin">
								<n-button size="small" secondary @click="openForm(waf)">Edit</n-button>
								<n-popconfirm @positive-click="remove(waf)">
									<template #trigger>
										<n-button size="small" secondary type="error" :loading="deleting === waf.id">
											Delete
										</n-button>
									</template>
									Remove "{{ waf.name }}" from CoPilot? Its token stays valid on the WAF until you
									revoke it there.
								</n-popconfirm>
							</template>
						</div>
					</div>
					<n-alert
						v-if="verifyResults[waf.id]"
						class="mt-3"
						:type="verifyResults[waf.id]?.authenticated ? 'success' : 'error'"
						:bordered="false"
					>
						<div class="flex flex-col gap-1 text-xs">
							<template v-if="verifyResults[waf.id]?.authenticated">
								<span>
									Connected as
									<b>{{ verifyResults[waf.id]?.waf_user_email }}</b>
									({{ verifyResults[waf.id]?.waf_roles.join(", ") }}) —
									{{ describeCapabilities(verifyResults[waf.id]!) }}
								</span>
							</template>
							<template v-else>
								<span>{{ verifyResults[waf.id]?.detail }}</span>
								<span v-if="reasonHint(verifyResults[waf.id]?.reason)" class="opacity-80">
									{{ reasonHint(verifyResults[waf.id]?.reason) }}
								</span>
							</template>
						</div>
					</n-alert>
					<CustomerWafForwarding
						:customer-code
						:instance="waf"
						:default-host="forwardingDefaultHost"
						:port-range="forwardingPortRange"
						@updated="replace"
					/>
				</n-card>
			</div>
		</n-spin>

		<CustomerWafForm v-model:show="showForm" :customer-code :instance="editing" @saved="onSaved" />
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { CustomerWafInstance, CustomerWafVerification } from "@/types/customer-waf"
import { NAlert, NButton, NCard, NEmpty, NPopconfirm, NSpin, NTag, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import { useRouter } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useAuthStore } from "@/stores/auth"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import CustomerWafError from "./CustomerWafError.vue"
import CustomerWafForm from "./CustomerWafForm.vue"
import CustomerWafForwarding from "./CustomerWafForwarding.vue"
import { invalidateCustomerWafs, reasonHint, wafCapabilityLabel } from "./utils"

const { customerCode } = defineProps<{ customerCode: string }>()

const AddIcon = "carbon:add"
const OpenIcon = "carbon:launch"
const router = useRouter()
const message = useMessage()
const dFormats = useSettingsStore().dateFormat
const isAdmin = computed(() => useAuthStore().isAdmin)

const loading = ref(false)
const error = ref<ApiError | null>(null)
const instances = ref<CustomerWafInstance[]>([])
const keyConfigured = ref(true)
const forwardingDefaultHost = ref<string | null>(null)
const forwardingPortRange = ref<string | null>(null)
const verifying = ref<number | null>(null)
const deleting = ref<number | null>(null)
const verifyResults = ref<Record<number, CustomerWafVerification>>({})
const showForm = ref(false)
const editing = ref<CustomerWafInstance | null>(null)

function describeCapabilities(v: CustomerWafVerification) {
	if (v.capabilities.can_block) return "CoPilot can read and block."
	if (v.capabilities.can_read) return "read-only: CoPilot can't block with this token."
	return "this role can't read the WAF's events."
}

function load() {
	loading.value = true
	error.value = null
	Api.customerWaf
		.getInstances(customerCode)
		.then(res => {
			instances.value = res.data.instances
			keyConfigured.value = res.data.encryption_key_configured
			forwardingDefaultHost.value = res.data.forwarding_default_host
			forwardingPortRange.value = res.data.forwarding_port_range
		})
		.catch((err: ApiError) => {
			error.value = err
		})
		.finally(() => {
			loading.value = false
		})
}

function replace(instance: CustomerWafInstance) {
	const idx = instances.value.findIndex(i => i.id === instance.id)
	if (idx === -1) instances.value.push(instance)
	else instances.value[idx] = instance
	invalidateCustomerWafs(customerCode)
}

// The live views live on the WAF page (Investigate → WAF); this tab is configuration only.
function openWafPage(waf: CustomerWafInstance) {
	router.push({ name: "Waf", query: { customer: waf.customer_code, waf: String(waf.id) } })
}

function verify(waf: CustomerWafInstance) {
	verifying.value = waf.id
	Api.customerWaf
		.verifyInstance(customerCode, waf.id)
		.then(res => {
			verifyResults.value[waf.id] = res.data.verification
			replace(res.data.instance)
		})
		.catch((err: ApiError) => {
			message.error(getApiErrorMessage(err) || "Connection test failed.")
		})
		.finally(() => {
			verifying.value = null
		})
}

function openForm(waf: CustomerWafInstance | null) {
	editing.value = waf
	showForm.value = true
}

function onSaved(e: { instance: CustomerWafInstance; verification: CustomerWafVerification | null; warnings: string[] }) {
	replace(e.instance)
	if (e.verification) verifyResults.value[e.instance.id] = e.verification
	else delete verifyResults.value[e.instance.id]
	for (const w of e.warnings) message.warning(w)
	message.success(`WAF "${e.instance.name}" saved`)
}

function remove(waf: CustomerWafInstance) {
	deleting.value = waf.id
	Api.customerWaf
		.deleteInstance(customerCode, waf.id)
		.then(res => {
			message.info(res.data.message, { duration: 8000 })
			instances.value = instances.value.filter(i => i.id !== waf.id)
			invalidateCustomerWafs(customerCode)
		})
		.catch((err: ApiError) => {
			message.error(getApiErrorMessage(err) || "Delete failed.")
		})
		.finally(() => {
			deleting.value = null
		})
}

onBeforeMount(load)
</script>
