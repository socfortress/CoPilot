import type { SSOCloudflareVerifyResponse, SSOPublicStatus } from "@/api/endpoints/sso"
import Api from "@/api"

export function ssoAzure() {
	window.location.href = "/api/auth/sso/azure/login"
}

export function ssoGoogle() {
	window.location.href = "/api/auth/sso/google/login"
}

export async function ssoCloudflare(cb?: (error: string | null, payload?: SSOCloudflareVerifyResponse) => void) {
	try {
		const res = await Api.sso.cloudflareVerify()
		cb?.(null, res.data)
	} catch (err: any) {
		cb?.(
			err.response?.data?.detail
				? err.response?.data?.detail?.toString()
				: "Cloudflare Access authentication failed. Make sure you are behind Cloudflare Access."
		)
	}
}

export async function getSSOStatus(cb?: (status: SSOPublicStatus) => void) {
	try {
		const res = await Api.sso.getStatus()
		cb?.(res.data)
	} catch {
		cb?.({
			sso_enabled: false,
			azure_enabled: false,
			google_enabled: false,
			cf_enabled: false,
			azure_authorization_url: null,
			google_authorization_url: null
		})
	}
}
