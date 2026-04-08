import type { CommonResponse } from "@/types/common"
import type { PortalSettings } from "@/types/portal"
import { HttpClient } from "../httpClient"

export default {
	getSettings() {
		return HttpClient.get<CommonResponse<{ settings: PortalSettings }>>("/customer_portal/settings")
	}
}
