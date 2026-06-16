<template>
	<n-card title="Passkeys">
		<template #header-extra>
			<n-tag :type="hasPasskeys ? 'success' : 'default'" size="small">
				{{ hasPasskeys ? `${passkeys.length} registered` : "No passkeys registered" }}
			</n-tag>
		</template>

		<n-spin :show="loading">
			<n-alert v-if="!browserSupported" type="warning" class="mb-4">
				Your browser does not support passkeys (WebAuthn).
			</n-alert>

			<n-alert v-else-if="!originSupported" type="warning" class="mb-4">
				Passkeys do not work on
				<code class="font-mono">127.0.0.1</code>
				. Open
				<a :href="localhostUrl" class="text-primary underline">{{ localhostUrl }}</a>
				instead.
			</n-alert>

			<n-alert v-if="!serverEnabled && !loading" type="info" class="mb-4">
				Passkeys are not configured on this server. Set
				<code class="font-mono">WEBAUTHN_ORIGINS</code>
				and
				<code class="font-mono">WEBAUTHN_RP_ID</code>
				in the deployment environment.
			</n-alert>

			<template v-else>
				<p class="text-secondary mb-4">
					Sign in with a passkey using your device biometrics or security key. Passkeys are phishing-resistant
					and work alongside your password.
				</p>

				<div v-if="passkeys.length" class="mb-4 flex flex-col gap-3">
					<div
						v-for="item in passkeys"
						:key="item.id"
						class="border-default flex items-center justify-between gap-3 rounded-lg border p-3"
					>
						<div class="flex min-w-0 flex-col gap-1">
							<span class="font-medium">{{ item.device_name }}</span>
							<span class="text-secondary text-xs">
								Added {{ formatDate(item.created_at, "MMM D, YYYY") }}
								<template v-if="item.last_used_at">
									· Last used {{ formatDate(item.last_used_at, "MMM D, YYYY") }}
								</template>
							</span>
						</div>
						<n-popconfirm @positive-click="removePasskey(item.id)">
							<template #trigger>
								<n-button size="small" type="error" secondary :loading="removingId === item.id">
									Remove
								</n-button>
							</template>
							Remove this passkey? You will no longer be able to sign in with it.
						</n-popconfirm>
					</div>
				</div>

				<n-button
					type="primary"
					:loading="registering"
					:disabled="!canRegisterPasskey"
					@click="openRegisterModal"
				>
					<template #icon>
						<Icon name="carbon:fingerprint-recognition" />
					</template>
					Add passkey
				</n-button>
			</template>
		</n-spin>

		<n-modal v-model:show="showRegisterModal" preset="card" title="Add passkey" :style="{ maxWidth: '420px' }">
			<div class="flex flex-col gap-4">
				<p class="text-secondary">
					Give this passkey a name so you can recognize the device later (e.g. MacBook, YubiKey).
				</p>
				<n-form-item label="Device name">
					<n-input
						v-model:value="deviceName"
						clearable
						:placeholder="defaultDeviceName"
						@keydown.enter="registerNewPasskey"
					/>
				</n-form-item>
				<div class="flex justify-end gap-2">
					<n-button @click="showRegisterModal = false">Cancel</n-button>
					<n-button type="primary" :loading="registering" @click="registerNewPasskey">Continue</n-button>
				</div>
			</div>
		</n-modal>
	</n-card>
</template>

<script lang="ts" setup>
import type { PasskeyItem } from "@/api/endpoints/passkey"
import type { ApiError } from "@/types/common"
import { NAlert, NButton, NCard, NFormItem, NInput, NModal, NPopconfirm, NSpin, NTag, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getDefaultPasskeyDeviceName, registerPasskey, usePasskeySupport } from "@/composables/usePasskey"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"

const message = useMessage()
const { isSupported: browserSupported, originSupported, localhostUrl } = usePasskeySupport()

const loading = ref(false)
const registering = ref(false)
const removingId = ref<number | null>(null)
const serverEnabled = ref(false)
const passkeys = ref<PasskeyItem[]>([])
const showRegisterModal = ref(false)
const defaultDeviceName = getDefaultPasskeyDeviceName()
const deviceName = ref(defaultDeviceName)

const hasPasskeys = computed(() => passkeys.value.length > 0)
const canRegisterPasskey = computed(() => browserSupported && originSupported)

async function loadStatus() {
	loading.value = true

	try {
		const [publicStatus, listRes] = await Promise.all([Api.passkey.getPublicStatus(), Api.passkey.listMine()])
		serverEnabled.value = publicStatus.data.enabled
		passkeys.value = listRes.data.passkeys || []
	} catch {
		serverEnabled.value = false
		passkeys.value = []
	} finally {
		loading.value = false
	}
}

function openRegisterModal() {
	if (!canRegisterPasskey.value) {
		return
	}
	deviceName.value = getDefaultPasskeyDeviceName()
	showRegisterModal.value = true
}

async function registerNewPasskey() {
	registering.value = true

	try {
		await registerPasskey(deviceName.value.trim() || getDefaultPasskeyDeviceName())
		showRegisterModal.value = false
		message.success("Passkey added successfully")
		await loadStatus()
	} catch (err) {
		if (err?.name === "NotAllowedError") {
			message.warning("Passkey registration was cancelled.")
			return
		}
		const detail = getApiErrorMessage(err as ApiError) || "Failed to register passkey"
		if (typeof detail === "string" && detail.toLowerCase().includes("invalid domain")) {
			message.error(`Passkeys require localhost. Open ${localhostUrl}`)
			return
		}
		message.error(detail)
	} finally {
		registering.value = false
	}
}

async function removePasskey(passkeyId: number) {
	removingId.value = passkeyId

	try {
		await Api.passkey.remove(passkeyId)
		message.success("Passkey removed")
		await loadStatus()
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Failed to remove passkey")
	} finally {
		removingId.value = null
	}
}

onBeforeMount(() => {
	loadStatus()
})
</script>
