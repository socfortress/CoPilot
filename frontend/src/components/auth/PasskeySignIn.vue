<template>
	<n-tooltip :disabled="!showTooltip">
		<template #trigger>
			<div>
				<n-button
					v-if="visible && !!username"
					size="large"
					class="animate-fade"
					:class="`${iconOnly ? 'w-10!' : 'w-full!'}`"
					:loading
					@click="signInWithPasskey"
				>
					<template #icon>
						<Icon name="carbon:fingerprint-recognition" />
					</template>
					<span v-if="!iconOnly">Passkey</span>
				</n-button>
			</div>
		</template>
		Sign in with passkey
	</n-tooltip>
</template>

<script lang="ts" setup>
import { NButton, NTooltip, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import { useRouter } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { usePasskeySupport } from "@/composables/usePasskey"
import { useAuthStore } from "@/stores/auth"

const props = defineProps<{
	username?: string
	showTooltip?: boolean
	iconOnly?: boolean
}>()

const emit = defineEmits<{
	(e: "show2faForm", value: string): void
	(e: "loginSuccess", value: string): void
}>()

const router = useRouter()
const authStore = useAuthStore()
const message = useMessage()
const { isSupported, originSupported, localhostUrl } = usePasskeySupport()

const loading = ref(false)
const serverEnabled = ref(false)

const visible = computed(() => isSupported && originSupported && serverEnabled.value)

async function loadStatus() {
	try {
		const res = await Api.passkey.getPublicStatus()
		serverEnabled.value = res.data.enabled
	} catch {
		serverEnabled.value = false
	}
}

async function signInWithPasskey() {
	loading.value = true

	try {
		const res = await authStore.loginWithPasskey(props.username)

		if (res?.requires_2fa) {
			emit("show2faForm", res.access_token)
			return
		}

		emit("loginSuccess", res.access_token)
		router.push({ path: "/", replace: true })
	} catch (err) {
		if (typeof err === "object" && err !== null && "name" in err && err.name === "NotAllowedError") {
			message.warning("Passkey sign-in was cancelled.")
			return
		}
		const detail = `${
			(typeof err === "object" && err !== null && "detail" in err ? err.detail : null) ||
			(typeof err === "object" && err !== null && "message" in err ? err.message : null) ||
			"Passkey sign-in failed"
		}`
		if (typeof detail === "string" && detail.toLowerCase().includes("invalid domain")) {
			message.error(`Passkeys require localhost. Open ${localhostUrl}`)
			return
		}
		message.error(detail)
	} finally {
		loading.value = false
	}
}

onBeforeMount(() => {
	loadStatus()
})
</script>
