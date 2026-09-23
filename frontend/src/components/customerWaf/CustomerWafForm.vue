<template>
	<n-modal
		v-model:show="show"
		preset="card"
		:title="instance ? `Edit WAF — ${instance.name}` : 'Add WAF'"
		:style="{ maxWidth: 'min(620px, 92vw)' }"
		segmented
		:mask-closable="!saving"
	>
		<n-form label-placement="top" :show-feedback="false" class="flex flex-col gap-4">
			<n-form-item label="Name">
				<n-input v-model:value="form.name" placeholder="e.g. prod-eu" :maxlength="100" />
			</n-form-item>

			<n-form-item label="WAF URL">
				<n-input v-model:value="form.api_url" placeholder="https://waf.example.com:8443" class="font-mono" />
			</n-form-item>
			<p class="text-secondary -mt-3 text-xs">
				The WAF admin UI address (it serves the API under /api). Plain http:// sends the token unencrypted.
			</p>

			<n-form-item label="Service token">
				<n-input
					v-model:value="form.service_token"
					type="password"
					show-password-on="click"
					class="font-mono"
					:placeholder="instance ? `${instance.token_prefix} — leave blank to keep` : 'wafst_…'"
					:input-props="{ autocomplete: 'off' }"
				/>
			</n-form-item>
			<p class="text-secondary -mt-3 text-xs">
				Issue it in the WAF under
				<b>Service Tokens</b>
				, for a dedicated user. Its WAF role sets what CoPilot can do:
				<b>viewer</b>
				reads,
				<b>admin</b>
				or
				<b>operator</b>
				can also block. It's stored encrypted and never shown again.
			</p>

			<div class="flex flex-wrap gap-6">
				<n-form-item label="Enabled" label-placement="left">
					<n-switch v-model:value="form.enabled" />
				</n-form-item>
				<n-form-item label="Verify TLS certificate" label-placement="left">
					<n-switch v-model:value="form.verify_tls" />
				</n-form-item>
			</div>
			<p v-if="!form.verify_tls" class="text-secondary -mt-3 text-xs">
				Off by default: a WAF's own self-signed certificate never covers its real address. Traffic is still
				encrypted.
			</p>
			<n-form-item v-else label="CA certificate (optional, PEM)">
				<n-input
					v-model:value="form.ca_cert_pem"
					type="textarea"
					class="font-mono text-xs"
					:autosize="{ minRows: 3, maxRows: 8 }"
					:placeholder="
						instance?.has_ca_cert ? 'A CA is stored — paste a new one to replace it' : '-----BEGIN CERTIFICATE-----'
					"
				/>
			</n-form-item>

			<CustomerWafError v-if="error" :error />
		</n-form>

		<template #footer>
			<div class="flex justify-end gap-3">
				<n-button :disabled="saving" @click="show = false">Cancel</n-button>
				<n-button type="primary" :loading="saving" :disabled="!canSave" @click="save()">
					{{ instance ? "Save" : "Add WAF" }}
				</n-button>
			</div>
		</template>
	</n-modal>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { CustomerWafInstance, CustomerWafPayload, CustomerWafVerification } from "@/types/customer-waf"
import { NButton, NForm, NFormItem, NInput, NModal, NSwitch } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import CustomerWafError from "./CustomerWafError.vue"
import { invalidateCustomerWafs } from "./utils"

const props = defineProps<{
	customerCode: string
	/** Editing this WAF; null adds a new one. */
	instance: CustomerWafInstance | null
}>()

const emit = defineEmits<{
	(
		e: "saved",
		value: { instance: CustomerWafInstance; verification: CustomerWafVerification | null; warnings: string[] }
	): void
}>()

const show = defineModel<boolean>("show", { default: false })

const saving = ref(false)
const error = ref<ApiError | null>(null)
const form = ref({ name: "", api_url: "", service_token: "", verify_tls: false, ca_cert_pem: "", enabled: true })

const canSave = computed(
	() => !!form.value.name.trim() && !!form.value.api_url.trim() && (!!props.instance || !!form.value.service_token.trim())
)

watch(show, open => {
	if (!open) return
	error.value = null
	const i = props.instance
	form.value = {
		name: i?.name ?? "",
		api_url: i?.api_url ?? "",
		// Write-only: never pre-filled, blank keeps the stored token.
		service_token: "",
		verify_tls: i?.verify_tls ?? false,
		ca_cert_pem: "",
		enabled: i?.enabled ?? true
	}
})

function save() {
	saving.value = true
	error.value = null
	const f = form.value
	const payload: CustomerWafPayload = {
		name: f.name.trim(),
		api_url: f.api_url.trim(),
		verify_tls: f.verify_tls,
		enabled: f.enabled,
		service_token: f.service_token.trim()
	}
	// Only send a CA when one was pasted, so saving without touching it keeps the stored CA.
	if (f.ca_cert_pem.trim()) payload.ca_cert_pem = f.ca_cert_pem.trim()

	const request = props.instance
		? Api.customerWaf.updateInstance(props.customerCode, props.instance.id, payload)
		: Api.customerWaf.createInstance(props.customerCode, payload)

	request
		.then(res => {
			invalidateCustomerWafs(props.customerCode)
			emit("saved", {
				instance: res.data.instance,
				verification: res.data.verification,
				warnings: res.data.warnings ?? []
			})
			show.value = false
		})
		.catch((err: ApiError) => {
			error.value = err
		})
		.finally(() => {
			saving.value = false
		})
}
</script>
