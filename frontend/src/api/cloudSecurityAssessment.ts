import { type FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "./httpClient"
import type {
	ScoutSuiteAwsReportPayload,
	ScoutSuiteAzureReportPayload,
	ScoutSuiteReport,
	ScoutSuiteReportPayload
} from "@/types/cloudSecurityAssessment.d"

export default {
	getAvailableScoutSuiteReports() {
		return HttpClient.get<FlaskBaseResponse & { available_reports: ScoutSuiteReport[] }>(
			`/scoutsuite/available-reports`
		)
	},
	getScoutSuiteReportGenerationOptions() {
		return HttpClient.get<FlaskBaseResponse & { options: string[] }>(`/scoutsuite/report-generation-options`)
	},
	generateAwsScoutSuiteReport(payload: ScoutSuiteReportPayload & ScoutSuiteAwsReportPayload) {
		return HttpClient.post<FlaskBaseResponse>(`/scoutsuite/generate-aws-report`, { ...payload, report_type: "aws" })
	},
	generateAzureScoutSuiteReport(payload: ScoutSuiteReportPayload & ScoutSuiteAzureReportPayload) {
		return HttpClient.post<FlaskBaseResponse>(`/scoutsuite/generate-azure-report`, {
			...payload,
			report_type: "azure"
		})
	},
	deleteScoutSuiteReport(reportName: string) {
		return HttpClient.delete<FlaskBaseResponse>(`/scoutsuite/delete-report/${reportName}`)
	}
}
