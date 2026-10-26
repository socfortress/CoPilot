import type { FlaskBaseResponse } from "@/types/flask"
import type { SocRequest, SocRequestsQuery } from "@/types/soc-requests"
import { HttpClient } from "../http-client"

/** "Ask the SOC" (#1305), the SOC's side: its customers' questions, and marking one answered. */
export default {
	list({ status, customerCodes, caseId, alertId }: SocRequestsQuery = {}, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { requests: SocRequest[]; total: number; open: number }>(
			"/customer_portal/soc_requests",
			{
				params: {
					...(status ? { status } : {}),
					...(customerCodes?.length ? { customer_codes: customerCodes } : {}),
					...(caseId ? { case_id: caseId } : {}),
					...(alertId ? { alert_id: alertId } : {})
				},
				paramsSerializer: { indexes: null },
				signal
			}
		)
	},
	/** A reply given outside CoPilot (by phone): a SOC comment on the case or alert answers it by itself. */
	markAnswered(requestId: number) {
		return HttpClient.post<FlaskBaseResponse & { request: SocRequest }>(
			`/customer_portal/soc_requests/${requestId}/answered`
		)
	}
}
