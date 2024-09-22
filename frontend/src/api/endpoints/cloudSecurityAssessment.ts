import type {
	ScoutSuiteAwsReportPayload,
	ScoutSuiteAzureReportPayload,
	ScoutSuiteGcpReportPayload,
	ScoutSuiteReport,
	ScoutSuiteReportPayload
} from "@/types/cloudSecurityAssessment.d"
import type { FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "../httpClient"

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
	generateGcpScoutSuiteReport(payload: ScoutSuiteReportPayload & ScoutSuiteGcpReportPayload) {
		const form = new FormData()
		form.append("file", new Blob([payload.file], { type: payload.file.type }), payload.file.name)

		return HttpClient.post<FlaskBaseResponse>(`/scoutsuite/generate-gcp-report`, form, {
			params: {
				report_name: payload.report_name
			}
		})
	},
	deleteScoutSuiteReport(reportName: string) {
		return HttpClient.delete<FlaskBaseResponse>(`/scoutsuite/delete-report/${reportName}`)
	}
}
