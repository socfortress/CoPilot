import type { AuditLogEntry, AuditLogFilters, AuditLogsListResponse, AuditVocabularies } from "@/types/audit"
import type { FlaskBaseResponse } from "@/types/flask"
import { HttpClient } from "../http-client"

export default {
	/** List audit log entries (admin only) with filtering + pagination. */
	getAuditLogs(filters?: AuditLogFilters, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & AuditLogsListResponse>("/audit", {
			params: filters,
			signal
		})
	},
	getAuditLog(auditId: number, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { audit_log: AuditLogEntry }>(`/audit/${auditId}`, { signal })
	},
	/** Action + result vocabularies, for populating filter dropdowns. */
	getAuditVocabularies() {
		return HttpClient.get<FlaskBaseResponse & AuditVocabularies>("/audit/actions")
	}
}
