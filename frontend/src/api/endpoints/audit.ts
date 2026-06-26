import type { AuditLogEntry, AuditLogFilters, AuditLogPagination, AuditVocabularies } from "@/types/audit"
import type { FlaskBaseResponse } from "@/types/flask"
import { HttpClient } from "../http-client"

export default {
	/** List audit log entries (admin only) with filtering + pagination. */
	getAuditLogs(filters?: AuditLogFilters) {
		return HttpClient.get<FlaskBaseResponse & { audit_logs: AuditLogEntry[]; pagination: AuditLogPagination }>(
			"/audit",
			{
				params: filters
			}
		)
	},
	/** Action + result vocabularies, for populating filter dropdowns. */
	getAuditVocabularies() {
		return HttpClient.get<FlaskBaseResponse & AuditVocabularies>("/audit/actions")
	}
}
