<template>
	<n-collapse-transition :show>
		<div class="flex flex-col">
			<n-divider>
				<span class="text-secondary text-xs">or sign in with</span>
			</n-divider>
			<div class="flex flex-col gap-3">
				<n-collapse-transition :show="ssoStatus?.azure_enabled || false">
					<n-button size="large" class="w-full!" @click="loginWithAzure">
						<template #icon>
							<Icon :name="AzureIcon" :size="18" />
						</template>
						Microsoft Entra ID
					</n-button>
				</n-collapse-transition>
				<n-collapse-transition :show="ssoStatus?.google_enabled || false">
					<n-button size="large" class="w-full!" @click="loginWithGoogle">
						<template #icon>
							<Icon :name="GoogleIcon" :size="18" />
						</template>
						Google
					</n-button>
				</n-collapse-transition>
				<n-collapse-transition :show="ssoStatus?.cf_enabled || false">
					<n-button size="large" class="w-full!" :loading="cfLoading" @click="loginWithCloudflare">
						<template #icon>
							<Icon :name="CloudflareIcon" :size="18" />
						</template>
						Cloudflare Access
					</n-button>
				</n-collapse-transition>
			</div>
		</div>
	</n-collapse-transition>
</template>

<script lang="ts" setup>
import type { SSOPublicStatus } from "@/api/endpoints/sso"
import { NButton, NCollapseTransition, NDivider, useMessage } from "naive-ui"
import { computed, onBeforeMount, onMounted, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"

const emit = defineEmits<{
	(e: "show2faForm", value: string): void
	(e: "loginSuccess", value: string): void
}>()

const AzureIcon = "devicon-plain:azure"
const GoogleIcon = "devicon-plain:googlecloud"
const CloudflareIcon = "simple-icons:cloudflare"

const cfLoading = ref(false)
const message = useMessage()
const ssoStatus = ref<SSOPublicStatus | null>(null)

const show = computed(() => {
	return (
		ssoStatus.value?.sso_enabled &&
		(ssoStatus.value.azure_enabled || ssoStatus.value.google_enabled || ssoStatus.value.cf_enabled)
	)
})

function loginWithAzure() {
	window.location.href = "/api/auth/sso/azure/login"
}

function loginWithGoogle() {
	window.location.href = "/api/auth/sso/google/login"
}

async function loginWithCloudflare() {
	cfLoading.value = true

	try {
		const res = await Api.sso.cloudflareVerify()
		if (res.data?.requires_2fa && res.data?.access_token) {
			// Cloudflare auth OK but user has 2FA — show verification step
			emit("show2faForm", res.data.access_token)
		} else if (res.data?.access_token) {
			emit("loginSuccess", res.data.access_token)
		}
	} catch (err: any) {
		message.error(
			err.response?.data?.detail
				? err.response?.data?.detail?.toString()
				: "Cloudflare Access authentication failed. Make sure you are behind Cloudflare Access."
		)
	} finally {
		cfLoading.value = false
	}
}

async function loadSSOStatus() {
	try {
		const res = await Api.sso.getStatus()
		ssoStatus.value = res.data
	} catch {
		ssoStatus.value = null
	}
}

onBeforeMount(() => {
	loadSSOStatus()
})

onMounted(() => {
	// Check if we're returning from SSO callback (token in URL fragment, not query)
	const params = new URLSearchParams(window.location.hash.substring(1) || window.location.search)
	const token = params.get("token")
	const requires2fa = params.get("requires_2fa")?.toLowerCase() === "true"

	if (params.has("token")) {
		params.delete("token")
	}
	if (params.has("requires_2fa")) {
		params.delete("requires_2fa")
	}

	if (token && requires2fa) {
		emit("show2faForm", token)
	} else if (token) {
		// Remove fragment from history so the token isn't stored in browser history
		history.replaceState(null, "", `${window.location.pathname}?${params.toString()}`)
		emit("loginSuccess", token)
	}
})
</script>
