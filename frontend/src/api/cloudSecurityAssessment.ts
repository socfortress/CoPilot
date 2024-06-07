import { type FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "./httpClient"
import type { ScoutSuiteReportPayload, ScoutSuiteReport } from "@/types/cloudSecurityAssessment.d"

export default {
	getAvailableScoutSuiteReports() {
		return HttpClient.get<FlaskBaseResponse & { available_reports: ScoutSuiteReport[] }>(
			`/scoutsuite/available-reports`
		)
	},
	getScoutSuiteReportGenerationOptions() {
		return HttpClient.get<FlaskBaseResponse & { options: string[] }>(`/scoutsuite/report-generation-options`)
	},
	generateAwsScoutSuiteReport(payload: ScoutSuiteReportPayload) {
		return HttpClient.post<FlaskBaseResponse>(`/scoutsuite/generate-aws-report`, { ...payload, report_type: "aws" })
	},
	deleteScoutSuiteReport(reportName: string) {
		return HttpClient.delete<FlaskBaseResponse>(`/scoutsuite/delete-report/${reportName}`)
	}
}
