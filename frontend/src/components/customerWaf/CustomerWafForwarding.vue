<template>
	<div class="border-default mt-3 flex flex-wrap items-center justify-between gap-3 border-t pt-3">
		<div class="flex min-w-0 flex-col gap-1">
			<span :class="SECTION_LABEL">Event forwarding (SIEM)</span>
			<div v-if="instance.forwarding_provisioned_at" class="flex flex-wrap items-center gap-2 text-xs">
				<n-tag size="small" round :bordered="false" type="success">
					<template #icon><Icon :name="OnIcon" :size="12" /></template>
					forwarding
				</n-tag>
				<span class="font-mono">syslog/tcp → {{ instance.syslog_host }}:{{ instance.syslog_port }}</span>
				<span class="text-secondary">
					since {{ formatDate(instance.forwarding_provisioned_at, dFormats.datetime) }}
				</span>
			</div>
			<span v-else class="text-secondary text-xs">
				Not set up — this WAF's events aren't in the SIEM, so they can't raise alerts.
			</span>
		</div>

		<template v-if="isAdmin">
			<n-popconfirm v-if="instance.forwarding_provisioned_at" @positive-click="remove()">
				<template #trigger>
					<n-button size="small" secondary :loading="removing">Stop forwarding</n-button>
				</template>
				Remove the WAF's forwarder and this WAF's Graylog input? Events already stored are kept.
			</n-popconfirm>
			<n-button v-else size="small" secondary type="primary" :disabled="!canForward" @click="openDialog()">
				<template #icon><Icon :name="ForwardIcon" /></template>
				Set up event forwarding
			</n-button>
		</template>

		<n-modal
			v-model:show="showDialog"
			preset="card"
			title="Set up event forwarding"
			:style="{ maxWidth: 'min(600px, 92vw)' }"
			segmented
			:mask-closable="!saving"
		>
			<div class="flex flex-col gap-4">
				<p class="text-secondary text-sm">
					CoPilot creates, and removes again if any step fails:
				</p>
				<ul class="text-secondary ml-4 flex list-disc flex-col gap-1 text-sm">
					<li>
						a Graylog
						<b>Syslog TCP input</b>
						for this WAF (no TLS) on a free port{{ portRange ? ` in ${portRange}` : "" }}, tagging every event
						with the customer and WAF name;
					</li>
					<li>
						the customer's
						<span class="font-mono">waf-{{ customerCode.toLowerCase() }}</span>
						index set (30-day retention, 1 shard) and WAF stream, if they don't exist yet;
					</li>
					<li>a syslog forwarder on the WAF pointing at that input, then the WAF's own test event.</li>
				</ul>

				<n-form-item label="Syslog destination (host or IP)" :show-feedback="false">
					<n-input v-model:value="host" placeholder="graylog.example.com" class="font-mono" />
				</n-form-item>
				<p class="text-secondary -mt-3 text-xs">
					The Graylog address
					<b>the WAF</b>
					can reach — often not the address CoPilot uses for Graylog's API.
				</p>

				<n-alert v-if="result" :type="result.test_success === false ? 'warning' : 'success'" :bordered="false">
					<div class="flex flex-col gap-1 text-sm">
						<span>{{ result.message }}</span>
						<span v-if="result.test_success" class="text-xs">The WAF's test event was sent.</span>
						<span v-for="w of result.warnings" :key="w" class="text-xs">{{ w }}</span>
						<span v-if="result.reused.length" class="text-xs opacity-80">Reused: {{ result.reused.join(", ") }}</span>
					</div>
				</n-alert>
				<CustomerWafError v-if="error" :error />
			</div>

			<template #footer>
				<div class="flex justify-end gap-3">
					<n-button :disabled="saving" @click="showDialog = false">{{ result ? "Close" : "Cancel" }}</n-button>
					<n-button v-if="!result" type="primary" :loading="saving" :disabled="!host.trim()" @click="setUp()">
						Set up
					</n-button>
				</div>
			</template>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { CustomerWafInstance } from "@/types/customer-waf"
import { NAlert, NButton, NFormItem, NInput, NModal, NPopconfirm, NTag, useMessage } from "naive-ui"
import { computed, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { SECTION_LABEL } from "@/components/common/section-label"
import { useAuthStore } from "@/stores/auth"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import CustomerWafError from "./CustomerWafError.vue"
import { capabilitiesFromRoles } from "./utils"

const { customerCode, instance, defaultHost, portRange } = defineProps<{
	customerCode: string
	instance: CustomerWafInstance
	defaultHost?: string | null
	portRange?: string | null
}>()

const emit = defineEmits<{ (e: "updated", value: CustomerWafInstance): void }>()

const OnIcon = "carbon:checkmark-filled"
const ForwardIcon = "carbon:data-share"
const message = useMessage()
const dFormats = useSettingsStore().dateFormat
const isAdmin = computed(() => useAuthStore().isAdmin)

// Creating the WAF-side forwarder needs a token whose WAF user is an admin.
const canForward = computed(() => instance.enabled && capabilitiesFromRoles(instance.last_verified_role).can_manage_forwarders)

const showDialog = ref(false)
const host = ref("")
const saving = ref(false)
const removing = ref(false)
const error = ref<ApiError | null>(null)
const result = ref<{ message: string; test_success: boolean | null; warnings: string[]; reused: string[] } | null>(null)

function openDialog() {
	host.value = instance.syslog_host ?? defaultHost ?? ""
	error.value = null
	result.value = null
	showDialog.value = true
}

function setUp() {
	saving.value = true
	error.value = null
	Api.customerWaf
		.setUpForwarding(customerCode, instance.id, host.value.trim())
		.then(res => {
			result.value = res.data
			emit("updated", res.data.instance)
		})
		.catch((err: ApiError) => {
			error.value = err
		})
		.finally(() => {
			saving.value = false
		})
}

function remove() {
	removing.value = true
	Api.customerWaf
		.removeForwarding(customerCode, instance.id)
		.then(res => {
			message.success(res.data.message)
			for (const w of res.data.warnings ?? []) message.warning(w, { duration: 8000 })
			emit("updated", res.data.instance)
		})
		.catch((err: ApiError) => {
			message.error(getApiErrorMessage(err) || "Removing forwarding failed.")
		})
		.finally(() => {
			removing.value = false
		})
}
</script>
