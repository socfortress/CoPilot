import type { CommonResponse } from "@/types/common"
import { HttpClient } from "../httpClient"

export interface PortalLanguages {
	locale: string
	available: string[]
}

/** The portal user's language (#1310): the server keeps the pick, so it follows them to any device. */
export default {
	/** Store the user's language: one enabled for at least one of their customers. */
	setMine(locale: string) {
		return HttpClient.put<CommonResponse<PortalLanguages>>("/customer_portal/languages/me", { locale })
	}
}
