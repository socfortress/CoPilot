import type { CaseEvent, CaseTask } from "@/types/caseTemplates"
import type { CommonResponse } from "@/types/common"
import { HttpClient } from "../httpClient"

// Read-only endpoints the customer portal consumes (issue #792).
// All write paths are gated to admin/analyst on the backend; this client
// intentionally exposes only GET surfaces so customers see what the SOC
// team is doing on their cases without being able to mutate.

export default {
	getCaseTasks(caseId: number) {
		return HttpClient.get<CommonResponse<{ tasks: CaseTask[] }>>(
			`/incidents/db_operations/case/${caseId}/tasks`
		)
	},
	getCaseTimeline(caseId: number, limit = 500, offset = 0) {
		return HttpClient.get<CommonResponse<{ case_id: number; events: CaseEvent[] }>>(
			`/incidents/db_operations/case/${caseId}/timeline`,
			{ params: { limit, offset } }
		)
	}
}
